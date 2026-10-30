// See WitheringStorm.h for this class's purpose, pattern and connections.

#include "WitheringStorm.h"

#include "Camera/CameraShakeBase.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "LSDefaultMeshes.h"
#include "RestorationSubsystem.h"
#include "SeedBall.h"

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
}

void AWitheringStorm::BeginPlay()
{
	Super::BeginPlay();

	StartZ = GetActorLocation().Z;
	SavedZ = StartZ;

	GetWorld()->GetSubsystem<URestorationSubsystem>()->OnNoteCollected.AddDynamic(this, &AWitheringStorm::HandleNoteCollected);
}

void AWitheringStorm::StartRising(ASeedBall* Ball)
{
	if (TargetBall)
	{
		return;
	}
	TargetBall = Ball;
	bRising = true;

	TargetBall->OnCheckpointSet.AddDynamic(this, &AWitheringStorm::HandleCheckpointSet);
	TargetBall->OnRespawned.AddDynamic(this, &AWitheringStorm::HandleBallRespawned);

	RumbleAudio->SetVolumeMultiplier(0.f);
	RumbleAudio->Play();
}

void AWitheringStorm::StopRising()
{
	bRising = false;
	RumbleAudio->Stop();
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

	SetStormZ(GetActorLocation().Z + RiseSpeed * DeltaSeconds);
	UpdateCloseEffects(DeltaSeconds);

	// Checked every frame because the storm moves into the ball, and the ball may be standing still.
	if (ASeedBall* Ball = GetBallInside())
	{
		Ball->Die();
	}
}

void AWitheringStorm::UpdateCloseEffects(float DeltaSeconds)
{
	const float StormTop = GetActorLocation().Z + Box->GetScaledBoxExtent().Z;
	const float Gap = TargetBall->GetActorLocation().Z - StormTop;

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
	if (bRising)
	{
		SetStormZ(GetActorLocation().Z - NotePushback);
	}
}

void AWitheringStorm::HandleCheckpointSet(FVector Location)
{
	// Save the storm's current height, or lower if that would put it too close to the new checkpoint.
	const float HalfHeight = Box->GetScaledBoxExtent().Z;
	SavedZ = FMath::Min(GetActorLocation().Z, Location.Z - RespawnClearance - HalfHeight);
}

void AWitheringStorm::HandleBallRespawned()
{
	if (bRising)
	{
		SetStormZ(SavedZ);
	}
}
