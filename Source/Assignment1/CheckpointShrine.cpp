// See CheckpointShrine.h for this class's purpose and connections.

#include "CheckpointShrine.h"

#include "Components/PointLightComponent.h"
#include "Components/SphereComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "NiagaraFunctionLibrary.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"

ACheckpointShrine::ACheckpointShrine()
{
	Trigger = CreateDefaultSubobject<USphereComponent>(TEXT("Trigger"));
	SetRootComponent(Trigger);
	Trigger->InitSphereRadius(200.f);
	Trigger->SetCollisionProfileName(TEXT("Trigger"));

	Mesh = CreateDefaultSubobject<UStaticMeshComponent>(TEXT("Mesh"));
	Mesh->SetupAttachment(Trigger);
	Mesh->SetMobility(EComponentMobility::Movable);
	Mesh->SetCollisionProfileName(TEXT("NoCollision"));

	Glow = CreateDefaultSubobject<UPointLightComponent>(TEXT("Glow"));
	Glow->SetupAttachment(Trigger);
	Glow->SetMobility(EComponentMobility::Movable);
	Glow->SetVisibility(false);
}

void ACheckpointShrine::OnBallOverlap(ASeedBall* Ball)
{
	if (bActivated)
	{
		return;
	}
	bActivated = true;

	const FVector RespawnLocation = GetActorLocation() + FVector(0.f, 0.f, RespawnHeight);
	Ball->SetCheckpoint(RespawnLocation);

	GetWorld()->GetSubsystem<URestorationSubsystem>()->LockInRestoration();

	Glow->SetVisibility(true);
	UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ActivateEffect, GetActorLocation());
	UGameplayStatics::PlaySoundAtLocation(this, ActivateSound, GetActorLocation());
	PlayActivateEffect();
}
