// See WitherBlob.h for this class's purpose, pattern and connections.

#include "WitherBlob.h"

#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LSDefaultMeshes.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"
#include "Sound/SoundBase.h"

AWitherBlob::AWitherBlob()
{
	PrimaryActorTick.bCanEverTick = true;

	Body = CreateDefaultSubobject<USphereComponent>(TEXT("Body"));
	SetRootComponent(Body);
	Body->InitSphereRadius(60.f);
	// Overlap everything except level geometry. The ball passes in and is detected, while walls still stop the sweep.
	Body->SetCollisionEnabled(ECollisionEnabled::QueryOnly);
	Body->SetCollisionObjectType(ECC_Pawn);
	Body->SetCollisionResponseToAllChannels(ECR_Overlap);
	Body->SetCollisionResponseToChannel(ECC_WorldStatic, ECR_Block);

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Body);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetStaticMesh(LSDefaultMeshes::Sphere());
	Mesh->SetRelativeScale3D(FVector(1.2f));
}

void AWitherBlob::BeginPlay()
{
	Super::BeginPlay();

	// The points are stored relative to the blob, which moves, so convert them to fixed world positions once.
	for (const FVector& Point : PatrolPoints)
	{
		WorldPatrolPoints.Add(GetActorTransform().TransformPosition(Point));
	}
	if (WorldPatrolPoints.IsEmpty())
	{
		WorldPatrolPoints.Add(GetActorLocation());
	}
}

void AWitherBlob::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	ContactCooldownRemaining = FMath::Max(ContactCooldownRemaining - DeltaSeconds, 0.f);
	ASeedBall* Ball = Cast<ASeedBall>(UGameplayStatics::GetPlayerPawn(this, 0));

	UpdateState(Ball, DeltaSeconds);

	// Checked every frame, not on overlap, so a ball that stays touching is hit again after the cooldown.
	if (Ball && !Ball->IsDead() && Body->IsOverlappingActor(Ball))
	{
		HandleBallContact(Ball);
	}
}

void AWitherBlob::UpdateState(ASeedBall* Ball, float DeltaSeconds)
{
	switch (State)
	{
	case EBlobState::Patrol:
		if (IsBallWithin(Ball, ChaseRadius))
		{
			State = EBlobState::Chase;
		}
		else if (MoveToward(WorldPatrolPoints[PatrolIndex], PatrolSpeed, DeltaSeconds))
		{
			// The modulo wraps back to the first point after the last one.
			PatrolIndex = (PatrolIndex + 1) % WorldPatrolPoints.Num();
		}
		break;

	case EBlobState::Chase:
		if (IsBallWithin(Ball, LoseRadius))
		{
			MoveToward(Ball->GetActorLocation(), ChaseSpeed, DeltaSeconds);
		}
		else
		{
			State = EBlobState::Return;
		}
		break;

	case EBlobState::Return:
		if (IsBallWithin(Ball, ChaseRadius))
		{
			State = EBlobState::Chase;
		}
		// shortcut: moves in a straight line, so a wall can hold it here until the ball comes back, add pathfinding if levels need it.
		else if (MoveToward(WorldPatrolPoints[PatrolIndex], ReturnSpeed, DeltaSeconds))
		{
			State = EBlobState::Patrol;
		}
		break;
	}
}

bool AWitherBlob::IsBallWithin(const ASeedBall* Ball, float Radius) const
{
	return Ball && !Ball->IsDead()
		&& FVector::DistSquared2D(Ball->GetActorLocation(), GetActorLocation()) <= FMath::Square(Radius);
}

bool AWitherBlob::MoveToward(const FVector& Target, float Speed, float DeltaSeconds)
{
	const FVector Location = GetActorLocation();
	const FVector ToTarget = FVector(Target.X - Location.X, Target.Y - Location.Y, 0.f);

	if (ToTarget.SizeSquared() <= FMath::Square(ArrivalDistance))
	{
		return true;
	}

	const FVector Next = Location + ToTarget.GetSafeNormal() * Speed * DeltaSeconds;

	// Find the ground under the next position. Only level geometry counts, so the ball and triggers are ignored.
	FHitResult Ground;
	FCollisionQueryParams Params(SCENE_QUERY_STAT(WitherBlobGround), false, this);
	const FVector TraceStart = FVector(Next.X, Next.Y, Location.Z + MaxStepHeight);
	const FVector TraceEnd = FVector(Next.X, Next.Y, Location.Z - HoverHeight - MaxDropHeight);
	if (!GetWorld()->LineTraceSingleByObjectType(Ground, TraceStart, TraceEnd, FCollisionObjectQueryParams(ECC_WorldStatic), Params))
	{
		return false; // No ground within reach: this is a ledge, so wait at the edge.
	}

	// The sweep stops the blob at walls.
	SetActorLocation(FVector(Next.X, Next.Y, Ground.ImpactPoint.Z + HoverHeight), true);
	return false;
}

void AWitherBlob::HandleBallContact(ASeedBall* Ball)
{
	// All three must be true: a form that can slam, moving down fast, and coming from above.
	const bool bSlammedFromAbove = Ball->GetCurrentFormData().bCanSlam
		&& Ball->GetVelocity().Z <= -SlamKillSpeed
		&& Ball->GetActorLocation().Z > GetActorLocation().Z;

	if (bSlammedFromAbove)
	{
		UGameplayStatics::PlaySoundAtLocation(this, DeathSound, GetActorLocation());
		PlayDeathEffect();
		Destroy();
		return;
	}

	if (ContactCooldownRemaining > 0.f)
	{
		return;
	}
	ContactCooldownRemaining = ContactCooldown;

	GetWorld()->GetSubsystem<URestorationSubsystem>()->DrainRestoration(RestorationDrain);

	FVector Away = (Ball->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
	if (Away.IsNearlyZero())
	{
		Away = GetActorForwardVector(); // The ball is exactly on top, so any direction will do.
	}
	Ball->Knockback(Away, KnockbackSpeed, KnockbackUpSpeed);

	UGameplayStatics::PlaySoundAtLocation(this, ContactSound, GetActorLocation());
	PlayContactEffect();
}
