// See SeedBall.h for this class's purpose, patterns and connections.

#include "SeedBall.h"

#include "Engine/OverlapResult.h"
#include "Camera/CameraComponent.h"
#include "Components/AudioComponent.h"
#include "Components/PointLightComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/StaticMesh.h"
#include "Engine/World.h"
#include "GameFramework/SpringArmComponent.h"
#include "Kismet/GameplayStatics.h"
#include "LSGameInstance.h"
#include "LSInteractable.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "PhysicalMaterials/PhysicalMaterial.h"
#include "Sound/SoundBase.h"
#include "TimerManager.h"
#include "UObject/ConstructorHelpers.h"

ASeedBall::ASeedBall()
{
	PrimaryActorTick.bCanEverTick = true;

	// The physics body must keep its own rotation, so the controller must not rotate the pawn.
	bUseControllerRotationPitch = false;
	bUseControllerRotationYaw = false;
	bUseControllerRotationRoll = false;

	BallMesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("BallMesh"));
	SetRootComponent(BallMesh);
	BallMesh->SetMobility(EComponentMobility::Movable);
	BallMesh->SetCollisionProfileName(UCollisionProfile::PhysicsActor_ProfileName);
	BallMesh->SetSimulatePhysics(true);
	// A fast slam could pass through thin geometry in one physics step. CCD prevents that.
	BallMesh->SetUseCCD(true);
	// Both are off by default for physics bodies. They power the ILSInteractable calls.
	BallMesh->SetGenerateOverlapEvents(true);
	BallMesh->SetNotifyRigidBodyCollision(true);

	// The engine sphere makes the pawn playable before any custom meshes exist.
	static ConstructorHelpers::FObjectFinder<UStaticMesh> SphereMesh(TEXT("/Engine/BasicShapes/Sphere.Sphere"));
	if (SphereMesh.Succeeded())
	{
		BallMesh->SetStaticMesh(SphereMesh.Object);
	}

	// The stencil value tells the withering post-process (see ARestorationDriver) to leave the player in full colour.
	constexpr int32 FullColourStencil = 1;

	RollingVisual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("RollingVisual"));
	RollingVisual->SetupAttachment(BallMesh);
	RollingVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	RollingVisual->SetRenderCustomDepth(true);
	RollingVisual->SetCustomDepthStencilValue(FullColourStencil);

	UprightVisual = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("UprightVisual"));
	UprightVisual->SetupAttachment(BallMesh);
	// Modelled around the ball's centre with no offset, so its top stays on top wherever the ball has turned.
	UprightVisual->SetUsingAbsoluteRotation(true);
	UprightVisual->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	UprightVisual->SetRenderCustomDepth(true);
	UprightVisual->SetCustomDepthStencilValue(FullColourStencil);

	GlowLight = CreateDefaultSubobject<UPointLightComponent>(TEXT("GlowLight"));
	GlowLight->SetupAttachment(BallMesh);
	GlowLight->SetIntensityUnits(ELightUnits::Candelas);
	GlowLight->SetAttenuationRadius(600.f);
	// The light sits inside the ball. With shadows on, the ball's own mesh would block it.
	GlowLight->SetCastShadows(false);

	GlowParticles = CreateDefaultSubobject<UNiagaraComponent>(TEXT("GlowParticles"));
	GlowParticles->SetupAttachment(BallMesh);
	GlowParticles->SetUsingAbsoluteRotation(true);

	SpringArm = CreateDefaultSubobject<USpringArmComponent>(TEXT("SpringArm"));
	SpringArm->SetupAttachment(BallMesh);
	// The ball spins constantly. The arm follows its position but takes rotation only from the controller.
	SpringArm->SetUsingAbsoluteRotation(true);
	SpringArm->bUsePawnControlRotation = true;
	SpringArm->TargetArmLength = 600.f;
	SpringArm->bEnableCameraLag = true;
	SpringArm->CameraLagSpeed = 8.f;
	SpringArm->bDoCollisionTest = true;

	Camera = CreateDefaultSubobject<UCameraComponent>(TEXT("Camera"));
	Camera->SetupAttachment(SpringArm, USpringArmComponent::SocketName);

	RollAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("RollAudio"));
	RollAudio->SetupAttachment(BallMesh);
	RollAudio->SetAutoActivate(false);

	// Default form values. All of them can be edited on the Blueprint child.
	FormData.Add(ESeedForm::Seed, FSeedFormData());

	FSeedFormData Stone;
	Stone.MassKg = 80.f;
	Stone.LinearDamping = 0.3f;
	Stone.AngularDamping = 1.5f;
	Stone.TorqueStrength = 25.f;
	Stone.MaxAngularSpeed = 420.f;
	Stone.JumpImpulse = 420.f;
	Stone.WindResponse = 0.05f;
	Stone.GravityScale = 1.3f;
	Stone.bBuoyancyEnabled = false;
	Stone.bCanSlam = true;
	Stone.GlowColor = FLinearColor(1.f, 0.6f, 0.2f);
	Stone.GlowBrightness = 12.f;
	FormData.Add(ESeedForm::Stone, Stone);

	FSeedFormData Dandelion;
	Dandelion.MassKg = 5.f;
	Dandelion.LinearDamping = 0.6f;
	Dandelion.AngularDamping = 1.2f;
	Dandelion.TorqueStrength = 30.f;
	Dandelion.MaxAngularSpeed = 600.f;
	Dandelion.JumpImpulse = 650.f;
	Dandelion.WindResponse = 1.5f;
	Dandelion.GravityScale = 0.6f;
	Dandelion.bFragile = true;
	Dandelion.bCanGlide = true;
	Dandelion.GlowColor = FLinearColor(1.f, 0.9f, 0.65f);
	Dandelion.GlowBrightness = 25.f;
	FormData.Add(ESeedForm::Dandelion, Dandelion);
}

void ASeedBall::BeginPlay()
{
	Super::BeginPlay();

	CheckpointLocation = GetActorLocation();
	CurrentForm = InitialForm;
	// Apply data directly: this is the starting state, not a switch, so no effect or event should fire.
	ApplyFormData(GetCurrentFormData());

	BallMesh->OnComponentBeginOverlap.AddDynamic(this, &ASeedBall::HandleBeginOverlap);
	BallMesh->OnComponentHit.AddDynamic(this, &ASeedBall::HandleHit);
}

void ASeedBall::HandleBeginOverlap(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult)
{
	// The cast fails harmlessly for actors that don't implement the interface.
	if (ILSInteractable* Interactable = Cast<ILSInteractable>(OtherActor))
	{
		Interactable->OnBallOverlap(this);
	}
}

void ASeedBall::HandleHit(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
	FVector NormalImpulse, const FHitResult& Hit)
{
	if (ILSInteractable* Interactable = Cast<ILSInteractable>(OtherActor))
	{
		Interactable->OnBallHit(this, PreImpactVelocity);
	}
}

void ASeedBall::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (bIsDead)
	{
		return;
	}

	PreImpactVelocity = BallMesh->GetPhysicsLinearVelocity();

	const FSeedFormData& Data = GetCurrentFormData();
	UpdateTimers(DeltaSeconds);
	UpdateGrounded();
	TryConsumeJump(Data);
	ApplyMovement(Data);
	ApplyTrailEdgeResistance();
	ApplyGravityScale(Data);
	ApplyGlide(Data);
	UpdateRollAudio(Data, DeltaSeconds);
}

void ASeedBall::UpdateRollAudio(const FSeedFormData& Data, float DeltaSeconds)
{
	// Checked here so the loop starts in one place: at the first frame of play, and again after each respawn.
	if (RollAudio->Sound && !RollAudio->IsPlaying())
	{
		RollAudio->Play();
	}

	// 0 when still and 1 at this form's top speed, so each form uses its whole range even though Stone is slower.
	const float Speed = BallMesh->GetPhysicsLinearVelocity().Size();
	const float SpeedFraction = FMath::Clamp(Speed / FMath::Max(GetMaxRollSpeed(Data), 1.f), 0.f, 1.f);

	// Silent in the air. Moving toward the target stops the sound from cutting in and out on small bumps.
	RollVolume = FMath::FInterpTo(RollVolume, bIsGrounded ? SpeedFraction : 0.f, DeltaSeconds, RollFadeSpeed);
	RollAudio->SetVolumeMultiplier(RollVolume);
	RollAudio->SetPitchMultiplier(FMath::Lerp(RollMinPitch, RollMaxPitch, SpeedFraction));
}

void ASeedBall::UpdateTimers(float DeltaSeconds)
{
	CoyoteTimeRemaining = FMath::Max(CoyoteTimeRemaining - DeltaSeconds, 0.f);
	JumpBufferRemaining = FMath::Max(JumpBufferRemaining - DeltaSeconds, 0.f);
	JumpLockoutRemaining = FMath::Max(JumpLockoutRemaining - DeltaSeconds, 0.f);
	FormCooldownRemaining = FMath::Max(FormCooldownRemaining - DeltaSeconds, 0.f);
}

void ASeedBall::UpdateGrounded()
{
	const bool bWasGrounded = bIsGrounded;

	// During the lockout the ball is still touching the ground, but it has already jumped.
	bIsGrounded = JumpLockoutRemaining <= 0.f && CheckForGround();

	if (!bIsGrounded)
	{
		AirFallSpeed = FMath::Max(-BallMesh->GetPhysicsLinearVelocity().Z, 0.f);
	}
	else if (!bWasGrounded && AirFallSpeed >= LandMinSpeed)
	{
		const float Volume = FMath::Min(AirFallSpeed / LandFullVolumeSpeed, 1.f);
		UGameplayStatics::PlaySoundAtLocation(this, LandSound, GetActorLocation(), Volume);
	}

	if (bIsGrounded)
	{
		// Standing on ground keeps the coyote window full. It only starts draining after leaving the ground.
		CoyoteTimeRemaining = CoyoteTime;

		if (bIsSlamming)
		{
			bIsSlamming = false;
			PlaySlamLandEffect();
		}
	}
}

bool ASeedBall::CheckForGround() const
{
	// A slightly smaller sphere avoids hitting walls that the ball is merely rolling against.
	const float SkinWidth = 2.f;
	const FCollisionShape Sphere = FCollisionShape::MakeSphere(BallRadius - SkinWidth);
	const FVector Start = GetActorLocation();
	const FVector End = Start - FVector(0.f, 0.f, SkinWidth + GroundCheckDistance);

	FCollisionQueryParams Params(SCENE_QUERY_STAT(SeedBallGroundCheck), false, this);
	FHitResult Hit;

	// Sweeping with the ball's own object channel finds whatever would physically block the ball.
	// Overlap-only volumes such as pickups and wind never count as ground.
	const bool bHit = GetWorld()->SweepSingleByChannel(
		Hit, Start, End, FQuat::Identity, BallMesh->GetCollisionObjectType(), Sphere, Params);

	// Reject steep surfaces, otherwise the ball could jump repeatedly up a wall.
	return bHit && Hit.ImpactNormal.Z >= MinGroundNormalZ;
}

void ASeedBall::TryConsumeJump(const FSeedFormData& Data)
{
	// Both windows must be open: a recent press (buffer) and recent ground contact (coyote).
	if (JumpBufferRemaining <= 0.f || CoyoteTimeRemaining <= 0.f)
	{
		return;
	}

	JumpBufferRemaining = 0.f;
	CoyoteTimeRemaining = 0.f;
	JumpLockoutRemaining = JumpLockoutTime;
	bIsGrounded = false;

	// Cancel any falling speed first so a coyote jump is as high as a normal jump.
	const float FallingSpeed = FMath::Min(BallMesh->GetPhysicsLinearVelocity().Z, 0.f);
	// bVelChange = true means this is a direct speed change, so mass does not affect jump height.
	BallMesh->AddImpulse(FVector(0.f, 0.f, Data.JumpImpulse - FallingSpeed), NAME_None, true);

	UGameplayStatics::PlaySoundAtLocation(this, Data.JumpSound ? Data.JumpSound.Get() : JumpSound.Get(), GetActorLocation());
}

void ASeedBall::ApplyMovement(const FSeedFormData& Data)
{
	if (MoveInput.IsNearlyZero())
	{
		return;
	}

	// Use camera yaw only: looking down must not push the ball into the floor.
	const FRotator CameraYaw(0.f, GetControlRotation().Yaw, 0.f);
	const FVector MoveDirection = CameraYaw.RotateVector(FVector(MoveInput.Y, MoveInput.X, 0.f)).GetClampedToMaxSize(1.f);

	if (bIsGrounded)
	{
		// To roll toward MoveDirection, the spin axis is Up x MoveDirection (the ball's top moves that way).
		// bAccelChange = true keeps rolling tuning independent of mass.
		const FVector Torque = (FVector::UpVector ^ MoveDirection) * Data.TorqueStrength;
		BallMesh->AddTorqueInRadians(Torque, NAME_None, true);
	}
	else
	{
		// Torque does nothing useful in the air, so steer with a direct force at reduced strength.
		// TorqueStrength * BallRadius converts spin acceleration into the matching linear acceleration.
		const float AirAcceleration = Data.TorqueStrength * BallRadius * AirControlFraction;

		// Only push while below rolling top speed, so air control can't build unlimited speed.
		const float SpeedAlongInput = FVector::DotProduct(BallMesh->GetPhysicsLinearVelocity(), MoveDirection);
		if (SpeedAlongInput < GetMaxRollSpeed(Data))
		{
			BallMesh->AddForce(MoveDirection * AirAcceleration, NAME_None, true);
		}
	}
}

void ASeedBall::ApplyTrailEdgeResistance()
{
	static const FName SoftTrailEdge(TEXT("LS_SoftTrailEdge"));
	constexpr float CushionWidth = 220.f;
	const FVector Center = BallMesh->GetComponentLocation();
	TArray<FOverlapResult> Nearby;
	GetWorld()->OverlapMultiByObjectType(Nearby, Center, FQuat::Identity,
		FCollisionObjectQueryParams(ECC_WorldStatic), FCollisionShape::MakeSphere(CushionWidth + BallRadius));

	float ClosestClearance = CushionWidth;
	FVector Inward = FVector::ZeroVector;
	for (const FOverlapResult& Overlap : Nearby)
	{
		const AActor* Wall = Overlap.GetActor();
		if (!Wall || !Wall->ActorHasTag(SoftTrailEdge)) continue;
		// Wildwood boundaries are rotated 100 cm cubes scaled to the segment's length and height.
		const FTransform Pose = Wall->GetActorTransform();
		const FVector Local = Pose.InverseTransformPositionNoScale(Center);
		const FVector Extent = Pose.GetScale3D().GetAbs() * 50.f;
		if (FMath::Abs(Local.Z) > Extent.Z + BallRadius) continue;
		const FVector Offset(Local.X - FMath::Clamp(Local.X, -Extent.X, Extent.X),
			Local.Y - FMath::Clamp(Local.Y, -Extent.Y, Extent.Y), 0.f);
		const float Clearance = Offset.Size() - BallRadius;
		if (Clearance >= ClosestClearance || Offset.IsNearlyZero()) continue;
		ClosestClearance = Clearance;
		Inward = Pose.TransformVectorNoScale(Offset.GetSafeNormal()).GetSafeNormal2D();
	}

	if (Inward.IsNearlyZero()) return;
	const float Depth = 1.f - FMath::Clamp(ClosestClearance / CushionWidth, 0.f, 1.f);
	const float ApproachSpeed = FMath::Max(0.f, -FVector::DotProduct(PreImpactVelocity, Inward));
	// Brake only motion toward the edge, leaving tangential rolling and jumps alone.
	const float Acceleration = 2400.f * FMath::Square(Depth) + 7.f * Depth * ApproachSpeed;
	BallMesh->AddForce(Inward * Acceleration, NAME_None, true);
}

float ASeedBall::GetMaxRollSpeed(const FSeedFormData& Data) const
{
	return FMath::DegreesToRadians(Data.MaxAngularSpeed) * BallRadius;
}

void ASeedBall::ApplyGravityScale(const FSeedFormData& Data)
{
	// The physics engine already applies gravity once, so only add the difference.
	// Example: GravityScale 0.6 adds -0.4 g, which is an upward push because GravityZ is negative.
	const float ExtraGravity = GetWorld()->GetGravityZ() * (Data.GravityScale - 1.f);
	BallMesh->AddForce(FVector(0.f, 0.f, ExtraGravity), NAME_None, true);
}

void ASeedBall::ApplyGlide(const FSeedFormData& Data)
{
	if (!Data.bCanGlide || !bJumpHeld || bIsGrounded)
	{
		return;
	}

	FVector Velocity = BallMesh->GetPhysicsLinearVelocity();
	if (Velocity.Z >= 0.f)
	{
		return; // Still rising: gliding only starts once the ball is falling.
	}

	BallMesh->AddForce(FVector(0.f, 0.f, GlideLiftAcceleration), NAME_None, true);

	if (Velocity.Z < -GlideMaxFallSpeed)
	{
		Velocity.Z = -GlideMaxFallSpeed;
		BallMesh->SetPhysicsLinearVelocity(Velocity);
	}
}

void ASeedBall::AddExternalAcceleration(const FVector& Acceleration)
{
	BallMesh->AddForce(Acceleration, NAME_None, true);
}

void ASeedBall::Knockback(const FVector& Direction, float HorizontalSpeed, float UpSpeed)
{
	BallMesh->SetPhysicsLinearVelocity(Direction * HorizontalSpeed + FVector::UpVector * UpSpeed);
}

void ASeedBall::SetCheckpoint(const FVector& Location)
{
	CheckpointLocation = Location;
	OnCheckpointSet.Broadcast(Location);
}

void ASeedBall::TeleportBall(const FVector& Location)
{
	SetActorLocation(Location, false, nullptr, ETeleportType::TeleportPhysics);
	BallMesh->SetPhysicsLinearVelocity(FVector::ZeroVector);
	BallMesh->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);
}

void ASeedBall::SetMoveInput(const FVector2D& Input)
{
	MoveInput = Input;
}

void ASeedBall::JumpPressed()
{
	bJumpHeld = true;
	if (!bIsDead)
	{
		// Only record the press here. Tick performs the jump as soon as the ball is allowed to.
		JumpBufferRemaining = JumpBufferTime;
	}
}

void ASeedBall::JumpReleased()
{
	bJumpHeld = false;
}

void ASeedBall::SlamPressed()
{
	if (bIsDead || bIsGrounded || bIsSlamming || !GetCurrentFormData().bCanSlam)
	{
		return;
	}

	bIsSlamming = true;
	// Cancel any upward speed so the slam starts immediately, even at the start of a jump.
	const float RisingSpeed = FMath::Max(BallMesh->GetPhysicsLinearVelocity().Z, 0.f);
	BallMesh->AddImpulse(FVector(0.f, 0.f, -SlamImpulse - RisingSpeed), NAME_None, true);
	PlaySlamStartEffect();
}

bool ASeedBall::TrySwitchForm(ESeedForm NewForm)
{
	if (bIsDead || NewForm == CurrentForm || FormCooldownRemaining > 0.f
		|| !FormData.Contains(NewForm) || !IsFormUnlocked(NewForm))
	{
		return false;
	}

	const ESeedForm OldForm = CurrentForm;
	OnExitForm(OldForm);
	CurrentForm = NewForm;
	OnEnterForm(NewForm);

	FormCooldownRemaining = FormSwitchCooldown;
	UGameplayStatics::PlaySoundAtLocation(this, FormSwitchSound, GetActorLocation());
	PlayFormSwitchEffect(OldForm, NewForm);
	OnFormChanged.Broadcast(OldForm, NewForm);
	return true;
}

void ASeedBall::CycleForm(int32 Direction)
{
	constexpr int32 FormCount = 3;
	const int32 Current = static_cast<int32>(CurrentForm);

	// Check the other two forms in order and switch to the first unlocked one.
	for (int32 Step = 1; Step < FormCount; ++Step)
	{
		// Adding FormCount keeps the value positive before the modulo when Direction is -1.
		const int32 Index = (Current + Direction * Step + FormCount) % FormCount;
		const ESeedForm Candidate = static_cast<ESeedForm>(Index);
		if (IsFormUnlocked(Candidate))
		{
			TrySwitchForm(Candidate);
			return;
		}
	}
}

const FSeedFormData& ASeedBall::GetCurrentFormData() const
{
	static const FSeedFormData Fallback;
	const FSeedFormData* Found = FormData.Find(CurrentForm);
	return Found ? *Found : Fallback;
}

bool ASeedBall::IsFormUnlocked(ESeedForm Form) const
{
	const ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>();
	return GameInstance && GameInstance->IsFormUnlocked(Form);
}

void ASeedBall::OnExitForm(ESeedForm OldForm)
{
	// A slam belongs to the form that started it, so it can't continue into a new form.
	bIsSlamming = false;
}

void ASeedBall::OnEnterForm(ESeedForm NewForm)
{
	ApplyFormData(GetCurrentFormData());
}

void ASeedBall::ApplyFormData(const FSeedFormData& Data)
{
	ApplyFormVisuals(Data);

	// SetSound restarts the loop if one is playing, so the new form's sound takes over straight away.
	RollAudio->SetSound(Data.RollSound);
	BallMesh->SetPhysMaterialOverride(Data.PhysicalMaterial);
	BallMesh->SetMassOverrideInKg(NAME_None, Data.MassKg, true);
	BallMesh->SetLinearDamping(Data.LinearDamping);
	BallMesh->SetAngularDamping(Data.AngularDamping);
	BallMesh->SetPhysicsMaxAngularVelocityInDegrees(Data.MaxAngularSpeed);
}

void ASeedBall::ApplyFormVisuals(const FSeedFormData& Data)
{
	RollingVisual->SetStaticMesh(Data.Mesh);
	RollingVisual->SetMaterial(0, Data.Material);
	UprightVisual->SetStaticMesh(Data.UprightMesh);
	UprightVisual->SetMaterial(0, Data.UprightMaterial);

	// Hiding the sphere does not affect its physics. A form with no mesh yet stays playable as the plain sphere.
	BallMesh->SetVisibility(Data.Mesh == nullptr);

	GlowLight->SetLightColor(Data.GlowColor);
	GlowLight->SetIntensity(Data.GlowBrightness);

	GlowParticles->SetAsset(Data.GlowEffect);
	if (Data.GlowEffect)
	{
		GlowParticles->Activate(true);
	}
}

void ASeedBall::FellOutOfWorld(const UDamageType& DamageType)
{
	Die(); // Deliberately skips Super, which would destroy the pawn.
}

void ASeedBall::Die()
{
	if (bIsDead)
	{
		return;
	}
	bIsDead = true;
	bIsSlamming = false;

	RollAudio->Stop();
	UGameplayStatics::PlaySoundAtLocation(this, DeathSound, GetActorLocation());
	PlayDeathEffect();
	OnDied.Broadcast();

	// Freeze and hide the ball so nothing can hit or kill it again while it waits.
	BallMesh->SetSimulatePhysics(false);
	SetActorEnableCollision(false);
	SetActorHiddenInGame(true);

	// SetTimer treats a rate of zero as "clear the timer", which would mean never respawning.
	GetWorldTimerManager().SetTimer(RespawnTimer, this, &ASeedBall::Respawn, FMath::Max(RespawnDelay, 0.01f), false);
}

void ASeedBall::Respawn()
{
	SetActorLocation(CheckpointLocation, false, nullptr, ETeleportType::TeleportPhysics);
	SetActorHiddenInGame(false);
	SetActorEnableCollision(true);
	BallMesh->SetSimulatePhysics(true);
	BallMesh->SetPhysicsLinearVelocity(FVector::ZeroVector);
	BallMesh->SetPhysicsAngularVelocityInRadians(FVector::ZeroVector);

	JumpBufferRemaining = 0.f;
	CoyoteTimeRemaining = 0.f;
	// Clear the fall that caused the death, or the first touch at the checkpoint would play a hard landing.
	AirFallSpeed = 0.f;
	RollVolume = 0.f;
	bIsDead = false;

	OnRespawned.Broadcast();
}
