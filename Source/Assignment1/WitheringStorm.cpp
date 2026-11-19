// See WitheringStorm.h for this class's purpose, pattern and connections.

#include "WitheringStorm.h"

#include "Camera/CameraShakeBase.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "LSDefaultMeshes.h"
#include "LSGameMode.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"
#include "RestorableActor.h"

AWitheringStorm::AWitheringStorm()
{
	PrimaryActorTick.bCanEverTick = true;

#if WITH_EDITORONLY_DATA
	// World Partition must not unload a storm that the player can only see from far above.
	bIsSpatiallyLoaded = false;
#endif

	Box->SetBoxExtent(FVector(5000.f, 5000.f, 500.f));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Box);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cube());
	// The cube is 100 cm wide, so these scales match the box above.
	Mesh->SetRelativeScale3D(FVector(100.f, 100.f, 10.f));

	RumbleAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("RumbleAudio"));
	RumbleAudio->SetupAttachment(Box);
	RumbleAudio->SetAutoActivate(false);
	AttackAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("AttackAudio"));
	AttackAudio->SetupAttachment(Box);
	AttackAudio->SetAutoActivate(false);
	AttackAudio->bAllowSpatialization = false;
}

void AWitheringStorm::BeginPlay()
{
	Super::BeginPlay();

	StartZ = GetActorLocation().Z;
	SavedZ = StartZ;
	if (FollowsPath())
	{
		SetProgress(0.f);
		// Out of sight until the chase starts, so the player never walks past a storm that is waiting for them.
		SetActorHiddenInGame(true);
	}

	GetWorld()->GetSubsystem<URestorationSubsystem>()->OnNoteCollected.AddDynamic(this, &AWitheringStorm::HandleNoteCollected);

	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->OnLevelCompleted.AddDynamic(this, &AWitheringStorm::StopRising);
	}
}

void AWitheringStorm::StartRising(ASeedBall* Ball)
{
	if (!IsValid(Ball) || TargetBall)
	{
		return;
	}
	TargetBall = Ball;
	bRising = true;
	DelayRemaining = StartDelay;

	TargetBall->OnCheckpointSet.AddDynamic(this, &AWitheringStorm::HandleCheckpointSet);
	TargetBall->OnRespawned.AddDynamic(this, &AWitheringStorm::HandleBallRespawned);

	RumbleAudio->SetVolumeMultiplier(0.f);
	RumbleAudio->Play();
	bWaveActive = false;
	SetActorHiddenInGame(bShockwaveAttacks);
}

void AWitheringStorm::StopRising()
{
	bRising = false;
	RumbleAudio->Stop();
	AttackAudio->Stop();
	bWaveActive = false;
	if (bShockwaveAttacks) SetActorHiddenInGame(true);
}

void AWitheringStorm::SetStormZ(float NewZ)
{
	FVector Location = GetActorLocation();
	Location.Z = FMath::Clamp(NewZ, StartZ, StartZ + MaxRiseDistance);
	SetActorLocation(Location);
}

void AWitheringStorm::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (!bRising)
	{
		return;
	}
	if (bShockwaveAttacks)
	{
		TickShockwave(DeltaSeconds);
		return;
	}
	DelayRemaining = FMath::Max(0.f, DelayRemaining - DeltaSeconds);
	if (DelayRemaining > 0.f) return;

	if (FollowsPath())
	{
		SetProgress(Progress + RiseSpeed * DeltaSeconds);
	}
	else
	{
		SetStormZ(GetActorLocation().Z + RiseSpeed * DeltaSeconds);
	}
	UpdateCloseEffects(DeltaSeconds);
	for (ARestorableActor* Tree : CurseTrees)
	{
		if (!IsValid(Tree) || Tree->IsCursed()) continue;
		const FVector Local = GetActorTransform().InverseTransformPosition(Tree->GetActorLocation());
		const FVector Extent = Box->GetUnscaledBoxExtent();
		if (FMath::Abs(Local.X) < Extent.X + 150.f && FMath::Abs(Local.Y) < Extent.Y + 200.f
			&& FMath::Abs(Local.Z) < Extent.Z + 400.f) Tree->SetCursed(true);
	}

	// Checked every frame because the storm moves into the ball, and the ball may be standing still.
	if (ASeedBall* Ball = GetBallInside())
	{
		Ball->Die();
	}
}

void AWitheringStorm::TickShockwave(float DeltaSeconds)
{
	if (!FollowsPath() || !IsValid(TargetBall) || TargetBall->IsDead()) return;
	DelayRemaining -= DeltaSeconds;
	if (!bWaveActive && DelayRemaining <= 0.f)
	{
		// Exclude the previous tier so successive attacks always change height.
		HeightTier = HeightTier < 0 ? FMath::RandRange(0, 2) : (HeightTier + FMath::RandRange(1, 2)) % 3;
		WaveHeight = 25.f + HeightTier * 25.f;
		SetProgress(0.f);
		DelayRemaining = FMath::FRandRange(6.f, 8.f);
		bWaveActive = true;
		SetActorHiddenInGame(false);
		AttackAudio->Play();
	}
	if (!bWaveActive) return;

	const FVector Previous = GetActorLocation();
	SetProgress(Progress + RiseSpeed * DeltaSeconds);
	const FVector Travel = GetActorLocation() - Previous;
	const FTransform Pose(GetActorRotation(), (Previous + GetActorLocation()) * .5f);
	FVector Extent = Box->GetScaledBoxExtent();
	// Sweep the thin wave through this frame's travel so a fast attack cannot tunnel past the seed.
	Extent.X += Travel.Size() * .5f;
	Extent.Z += FMath::Abs(Travel.Z) * .5f;
	const FVector Local = Pose.InverseTransformPosition(TargetBall->GetActorLocation());
	const auto CurveX = [this, Extent](float Y)
	{
		return -ShockwaveBend * FMath::Square(FMath::Clamp(Y / Extent.Y, -1.f, 1.f));
	};
	const UStaticMeshComponent* Body = TargetBall->FindComponentByClass<UStaticMeshComponent>();
	FVector BodyMin, BodyMax;
	if (Body) Body->GetLocalBounds(BodyMin, BodyMax);
	const float Radius = Body ? (BodyMax - BodyMin).GetMin() * .5f * Body->GetComponentScale().GetAbsMin() : 50.f;
	if (FMath::Abs(Local.X - CurveX(Local.Y)) < Extent.X + Radius && FMath::Abs(Local.Y) < Extent.Y + Radius
		&& FMath::Abs(Local.Z) < Extent.Z + Radius) TargetBall->Die();
	for (ARestorableActor* Tree : CurseTrees)
	{
		if (!IsValid(Tree) || Tree->IsCursed()) continue;
		const FVector TreeLocal = Pose.InverseTransformPosition(Tree->GetActorLocation());
		if (FMath::Abs(TreeLocal.X - CurveX(TreeLocal.Y)) < Extent.X + 150.f && FMath::Abs(TreeLocal.Y) < Extent.Y + 200.f
			&& FMath::Abs(TreeLocal.Z) < Extent.Z + 400.f) Tree->SetCursed(true);
	}
	if (Progress >= FMath::Min(GetPathLength(), MaxRiseDistance))
	{
		bWaveActive = false;
		SetActorHiddenInGame(true);
	}
}

void AWitheringStorm::UpdateCloseEffects(float DeltaSeconds)
{
	// Along the path, the gap is from the storm's front to the ball. Rising, it is from the storm's top.
	const float Gap = FollowsPath()
		? PathDistanceOf(TargetBall->GetActorLocation()) - (Progress + Box->GetScaledBoxExtent().X)
		: TargetBall->GetActorLocation().Z - (GetActorLocation().Z + Box->GetScaledBoxExtent().Z);

	// 0 when the storm is at Close Distance or further away, and 1 when it reaches the ball.
	const float Closeness = 1.f - FMath::Clamp(Gap / CloseDistance, 0.f, 1.f);
	RumbleAudio->SetVolumeMultiplier(Closeness);

	ShakeTimeRemaining -= DeltaSeconds;
	if (CloseShake && Closeness > 0.f && ShakeTimeRemaining <= 0.f)
	{
		ShakeTimeRemaining = ShakeInterval;
		if (APlayerController* PlayerController = TargetBall->GetController<APlayerController>())
		{
			PlayerController->ClientStartCameraShake(CloseShake, Closeness);
		}
	}
}

void AWitheringStorm::HandleNoteCollected(FVector Location)
{
	if (bRising && !bShockwaveAttacks)
	{
		if (FollowsPath())
		{
			SetProgress(Progress - NotePushback);
		}
		else
		{
			SetStormZ(GetActorLocation().Z - NotePushback);
		}
	}
}

void AWitheringStorm::HandleCheckpointSet(FVector Location)
{
	// Save the storm's current height, or lower if that would put it too close to the new checkpoint.
	const float HalfHeight = Box->GetScaledBoxExtent().Z;
	SavedZ = FMath::Min(GetActorLocation().Z, Location.Z - RespawnClearance - HalfHeight);
	SavedProgress = FMath::Min(Progress, PathDistanceOf(Location) - RespawnClearance - Box->GetScaledBoxExtent().X);
	bCheckpointInChase = true;
}

void AWitheringStorm::HandleBallRespawned()
{
	for (ARestorableActor* Tree : CurseTrees)
		if (IsValid(Tree)) Tree->SetCursed(false);
	if (bShockwaveAttacks || !CurseTrees.IsEmpty()) bCheckpointInChase = false;
	if (bRising)
	{
		if (FollowsPath() && !bCheckpointInChase)
		{
			// The ball is back behind the trigger: call the chase off, so it starts over when the ball passes it again.
			StopRising();
			TargetBall->OnCheckpointSet.RemoveDynamic(this, &AWitheringStorm::HandleCheckpointSet);
			TargetBall->OnRespawned.RemoveDynamic(this, &AWitheringStorm::HandleBallRespawned);
			TargetBall = nullptr;
			SetProgress(0.f);
			SetActorHiddenInGame(true);
		}
		else if (FollowsPath())
		{
			SetProgress(SavedProgress);
		}
		else
		{
			SetStormZ(SavedZ);
		}
	}
}

float AWitheringStorm::GetPathLength() const
{
	float Length = 0.f;
	for (int32 Index = 1; Index < ChasePoints.Num(); ++Index)
	{
		Length += FVector::Dist(ChasePoints[Index - 1], ChasePoints[Index]);
	}
	return Length;
}

void AWitheringStorm::SetProgress(float NewProgress)
{
	Progress = FMath::Clamp(NewProgress, 0.f, FMath::Min(GetPathLength(), MaxRiseDistance));
	// Walk the path to the segment holding Progress, then sit there, facing along it.
	float Remaining = Progress;
	for (int32 Index = 1; Index < ChasePoints.Num(); ++Index)
	{
		const FVector Segment = ChasePoints[Index] - ChasePoints[Index - 1];
		const float Length = Segment.Size();
		if (Remaining <= Length || Index == ChasePoints.Num() - 1)
		{
			const float Alpha = Length > 0.f ? FMath::Clamp(Remaining / Length, 0.f, 1.f) : 0.f;
			const FVector HeightOffset(0.f, 0.f, bShockwaveAttacks ? WaveHeight : 0.f);
			SetActorLocationAndRotation(ChasePoints[Index - 1] + Segment * Alpha + HeightOffset, FRotator(0.f, Segment.Rotation().Yaw, 0.f));
			return;
		}
		Remaining -= Length;
	}
}

float AWitheringStorm::PathDistanceOf(const FVector& Location) const
{
	// The distance along the path of the point on it nearest to Location, judged on the ground plane.
	float Best = TNumericLimits<float>::Max();
	float BestDistance = 0.f;
	float Walked = 0.f;
	for (int32 Index = 1; Index < ChasePoints.Num(); ++Index)
	{
		const FVector2D A(ChasePoints[Index - 1]), B(ChasePoints[Index]), P(Location);
		const FVector2D Segment = B - A;
		const float Length = Segment.Size();
		const float Along = Length > 0.f ? FMath::Clamp(FVector2D::DotProduct(P - A, Segment) / Length, 0.f, Length) : 0.f;
		const float Away = FVector2D::DistSquared(P, A + Segment.GetSafeNormal() * Along);
		if (Away < Best)
		{
			Best = Away;
			BestDistance = Walked + Along;
		}
		Walked += Length;
	}
	return BestDistance;
}
