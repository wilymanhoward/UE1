// See ThinIce.h for this class's purpose, pattern and connections.

#include "ThinIce.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/CollisionProfile.h"
#include "LSDefaultMeshes.h"
#include "SeedBall.h"
#include "TimerManager.h"

AThinIce::AThinIce()
{
	PrimaryActorTick.bCanEverTick = true;

	// Narrower than the ice, so a heavy ball must really be on it, not just touching its edge.
	Box->SetBoxExtent(FVector(85.f, 85.f, 50.f));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Box);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(UCollisionProfile::BlockAll_ProfileName);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cube());
	// A 10 cm slab whose top meets the bottom of the box.
	Mesh->SetRelativeScale3D(FVector(2.f, 2.f, 0.1f));
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, -55.f));
}

void AThinIce::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	if (bBroken)
	{
		return;
	}

	// Checked every frame, not on overlap, so switching to Stone while on the ice breaks it too.
	const ASeedBall* Ball = GetBallInside();
	if (Ball && Ball->GetCurrentFormData().MassKg >= BreakMassKg)
	{
		Break();
	}
}

void AThinIce::Break()
{
	bBroken = true;
	Mesh->SetVisibility(false);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	PlayBreakEffect();

	if (RestoreDelay > 0.f)
	{
		GetWorldTimerManager().SetTimer(RestoreTimer, this, &AThinIce::Restore, RestoreDelay, false);
	}
}

void AThinIce::Restore()
{
	bBroken = false;
	Mesh->SetVisibility(true);
	Mesh->SetCollisionEnabled(ECollisionEnabled::QueryAndPhysics);
}
