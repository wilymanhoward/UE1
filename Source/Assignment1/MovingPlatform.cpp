// See MovingPlatform.h for this class's purpose and connections.

#include "MovingPlatform.h"

#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LSDefaultMeshes.h"
#include "SeedBall.h"

namespace
{
	// Friction alone can't carry a ball: it rolls in place while the platform slides out from under it.
	// So a ball resting on the platform moves with it, keeping its own velocity on top.
	void CarryRider(AActor* Platform, UPrimitiveComponent* Surface, const FVector& Delta)
	{
		ASeedBall* Ball = Cast<ASeedBall>(UGameplayStatics::GetPlayerPawn(Platform, 0));
		if (Delta.IsNearlyZero() || !Ball || Ball->IsDead())
		{
			return;
		}
		const FVector From = Ball->GetActorLocation();
		FHitResult Hit;
		FCollisionQueryParams Params(SCENE_QUERY_STAT(MovingPlatformRider), true, Ball);
		// Down past the ball's 50 cm radius to whatever it rests on.
		if (Platform->GetWorld()->LineTraceSingleByChannel(Hit, From, From - FVector(0.f, 0.f, 80.f), ECC_Visibility, Params)
			&& Hit.GetComponent() == Surface)
		{
			Ball->AddActorWorldOffset(Delta, false, nullptr, ETeleportType::TeleportPhysics);
		}
	}
}

AMovingPlatform::AMovingPlatform()
{
	PrimaryActorTick.bCanEverTick = true;

	Path = CreateDefaultSubobject<USplineComponent>(TEXT("Path"));
	SetRootComponent(Path);
	Path->SetLocationAtSplinePoint(1, FVector(800.f, 0.f, 0.f), ESplineCoordinateSpace::Local);

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Path);
	// Movable and not simulating makes this a kinematic body, which physics treats as moving with real velocity.
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cube());
	Mesh->SetRelativeScale3D(FVector(3.f, 3.f, 0.3f));
}

void AMovingPlatform::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	// Here and not in BeginPlay, so the viewport shows the closed loop while designing the level.
	Path->SetClosedLoop(bLoop);
}

void AMovingPlatform::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (WaitRemaining > 0.f)
	{
		WaitRemaining -= DeltaSeconds;
		return;
	}

	const float PathLength = Path->GetSplineLength();
	DistanceAlongPath += Direction * Speed * DeltaSeconds;

	if (DistanceAlongPath <= 0.f || DistanceAlongPath >= PathLength)
	{
		if (bLoop)
		{
			DistanceAlongPath = FMath::Fmod(DistanceAlongPath, PathLength);
		}
		else
		{
			DistanceAlongPath = FMath::Clamp(DistanceAlongPath, 0.f, PathLength);
			Direction = -Direction;
		}
		WaitRemaining = WaitTime;
	}

	// Teleported, so physics gives the platform no velocity: friction would spin the ball up, and it rolled off the
	// end as the platform paused. CarryRider moves the ball with the platform instead.
	const FVector Before = Mesh->GetComponentLocation();
	Mesh->SetWorldLocation(Path->GetLocationAtDistanceAlongSpline(DistanceAlongPath, ESplineCoordinateSpace::World), false, nullptr,
		ETeleportType::TeleportPhysics);
	CarryRider(this, Mesh, Mesh->GetComponentLocation() - Before);
}
