// See WindVolume.h for this class's purpose, pattern and connections.

#include "WindVolume.h"

#include "Components/ArrowComponent.h"
#include "Components/AudioComponent.h"
#include "Components/BoxComponent.h"
#include "Engine/World.h"
#include "NiagaraComponent.h"
#include "PressurePlate.h"
#include "SeedBall.h"

AWindVolume::AWindVolume()
{
	PrimaryActorTick.bCanEverTick = true;

	Particles = CreateDefaultSubobject<UNiagaraComponent>(TEXT("Particles"));
	Particles->SetupAttachment(Box);
	// Tick turns it on once the wind is confirmed to be blowing.
	Particles->SetAutoActivate(false);

	WindAudio = CreateDefaultSubobject<UAudioComponent>(TEXT("WindAudio"));
	WindAudio->SetupAttachment(Box);
	WindAudio->SetAutoActivate(false);

	DirectionArrow = CreateDefaultSubobject<UArrowComponent>(TEXT("DirectionArrow"));
	DirectionArrow->SetupAttachment(Box);
	DirectionArrow->ArrowSize = 4.f;
}

void AWindVolume::OnConstruction(const FTransform& Transform)
{
	Super::OnConstruction(Transform);

	// The arrow is editor-only, so it doesn't exist in a packaged game.
	if (DirectionArrow)
	{
		DirectionArrow->SetWorldRotation(WindDirection.Rotation());
	}
}

bool AWindVolume::IsWindActive() const
{
	if (PowerPlate && !PowerPlate->IsPressed())
	{
		return false;
	}
	if (!bPulsing)
	{
		return true;
	}

	// Where we are in the on-then-off cycle. Using world time means no timer state to keep.
	const float CycleTime = FMath::Fmod(GetWorld()->GetTimeSeconds() + PulseOffset, PulseOnTime + PulseOffTime);
	return CycleTime < PulseOnTime;
}

void AWindVolume::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	const bool bActive = IsWindActive();
	if (bActive != bWasActive)
	{
		bWasActive = bActive;
		if (bActive)
		{
			Particles->Activate(true);
			WindAudio->FadeIn(SoundFadeTime);
		}
		else
		{
			Particles->Deactivate();
			WindAudio->FadeOut(SoundFadeTime, 0.f);
		}
		PlayWindActiveEffect(bActive);
	}

	if (!bActive)
	{
		return;
	}

	if (ASeedBall* Ball = GetBallInside())
	{
		const float Acceleration = Strength * Ball->GetCurrentFormData().WindResponse;
		Ball->AddExternalAcceleration(WindDirection.GetSafeNormal() * Acceleration);
	}
}
