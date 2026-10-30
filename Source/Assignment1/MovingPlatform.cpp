// See MovingPlatform.h for this class's purpose and connections.

#include "MovingPlatform.h"

#include "Components/SplineComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "LSDefaultMeshes.h"

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

	// A move with no teleport flag sets a kinematic target. Physics gets a velocity from it,
	// and that velocity is what lets friction carry the ball along.
	Mesh->SetWorldLocation(Path->GetLocationAtDistanceAlongSpline(DistanceAlongPath, ESplineCoordinateSpace::World));
}
