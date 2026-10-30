// See HazardVolume.h for this class's purpose, pattern and connections.

#include "HazardVolume.h"

#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "LSDefaultMeshes.h"
#include "SeedBall.h"

AHazardVolume::AHazardVolume()
{
	PrimaryActorTick.bCanEverTick = true;

	Box->SetBoxExtent(FVector(200.f, 200.f, 50.f));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Box);
	Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
	Mesh->SetStaticMesh(LSDefaultMeshes::Cone());
	Mesh->SetRelativeScale3D(FVector(4.f, 4.f, 1.f));
}

void AHazardVolume::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// Checked every frame, not on overlap, so switching from Stone to Seed inside the thorns is still fatal.
	ASeedBall* Ball = GetBallInside();
	if (!Ball)
	{
		return;
	}

	const FSeedFormData& Data = Ball->GetCurrentFormData();
	if (Data.bFragile || Data.MassKg < SurviveMassKg)
	{
		Ball->Die();
	}
	else if (GetWorld()->GetTimeSeconds() >= NextKnockbackTime)
	{
		NextKnockbackTime = GetWorld()->GetTimeSeconds() + KnockbackCooldown;
		Knockback(Ball);
	}
}

void AHazardVolume::Knockback(ASeedBall* Ball)
{
	// Send the ball back the way it came. A ball that isn't moving is pushed away from the centre instead.
	FVector Away = (-Ball->GetVelocity()).GetSafeNormal2D();
	if (Away.IsNearlyZero())
	{
		Away = (Ball->GetActorLocation() - GetActorLocation()).GetSafeNormal2D();
	}

	Ball->Knockback(Away, KnockbackSpeed, KnockbackUpSpeed);
	PlayKnockbackEffect();
}
