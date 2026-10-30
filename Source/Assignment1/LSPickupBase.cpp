// See LSPickupBase.h for this class's purpose, pattern and connections.

#include "LSPickupBase.h"

#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"

ALSPickupBase::ALSPickupBase()
{
	PrimaryActorTick.bCanEverTick = true;

	Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
	SetRootComponent(Trigger);
	Trigger->InitSphereRadius(80.f);
	// The Trigger profile overlaps everything and blocks nothing, so the ball rolls straight through.
	Trigger->SetCollisionProfileName(TEXT("Trigger"));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Trigger);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(TEXT("NoCollision"));
}

void ALSPickupBase::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	// A sine wave gives smooth up-and-down motion that slows at the top and bottom.
	const float BobOffset = FMath::Sin(GetGameTimeSinceCreation() * BobSpeed) * BobHeight;
	Mesh->SetRelativeLocation(FVector(0.f, 0.f, BobOffset));
	Mesh->AddLocalRotation(FRotator(0.f, SpinSpeed * DeltaSeconds, 0.f));
}

void ALSPickupBase::OnBallOverlap(ASeedBall* Ball)
{
	// Destroy doesn't take effect instantly, so a second overlap event must not collect again.
	if (bCollected)
	{
		return;
	}
	bCollected = true;

	OnCollected(Ball);

	// Both functions safely do nothing when no asset is assigned.
	UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, CollectEffect, GetActorLocation());
	UGameplayStatics::PlaySoundAtLocation(this, CollectSound, GetActorLocation());

	Destroy();
}
