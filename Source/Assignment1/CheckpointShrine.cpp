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

	// Ticks only while the lantern is fading in.
	PrimaryActorTick.bCanEverTick = true;
	PrimaryActorTick.bStartWithTickEnabled = false;
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

	// The light sits in the lantern, so the flame, sparkle and sound all start there. Tick brightens it from dark.
	FullIntensity = Glow->Intensity;
	LightAlpha = 0.f;
	Glow->SetIntensity(0.f);
	Glow->SetVisibility(true);
	SetActorTickEnabled(true);
	UNiagaraFunctionLibrary::SpawnSystemAtLocation(this, ActivateEffect, Glow->GetComponentLocation());
	UGameplayStatics::PlaySoundAtLocation(this, ActivateSound, Glow->GetComponentLocation());
	PlayActivateEffect();
}

void ACheckpointShrine::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	LightAlpha = LightFadeTime > 0.f ? FMath::Min(LightAlpha + DeltaSeconds / LightFadeTime, 1.f) : 1.f;
	// Eased in and out, so the flame catches softly and settles rather than ramping in a straight line.
	const float Brightness = FMath::SmoothStep(0.f, 1.f, LightAlpha);
	Glow->SetIntensity(FullIntensity * Brightness);
	Mesh->SetScalarParameterValueOnMaterials(TEXT("Lit"), Brightness);
	if (LightAlpha >= 1.f)
	{
		SetActorTickEnabled(false);
	}
}
