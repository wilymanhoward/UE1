// See AdaptiveMusicComponent.h for this class's purpose, pattern and connections.

#include "AdaptiveMusicComponent.h"

#include "Components/AudioComponent.h"
#include "Engine/World.h"
#include "Kismet/GameplayStatics.h"
#include "LSGameMode.h"
#include "RestorationSubsystem.h"
#include "Sound/SoundBase.h"

void UAdaptiveMusicComponent::BeginPlay()
{
	Super::BeginPlay();

	// Starting every stem in the same frame is what keeps them in sync, so a stem never starts at its milestone.
	for (USoundBase* Stem : Stems)
	{
		// bAutoDestroy is false because these components are kept and faded for the whole level.
		// CreateSound2D returns null when the sound is empty, which FadeInStem allows for.
		UAudioComponent* Audio = UGameplayStatics::CreateSound2D(this, Stem, 1.f, 1.f, 0.f, nullptr, false, false);
		if (Audio)
		{
			// CreateSound2D defaults to UI audio, which would keep the forest stems playing under the intro.
			Audio->bIsUISound = false;
			// A duration of 0 starts it at this volume straight away. The fade volume is multiplied by the component's
			// volume multiplier, so the multiplier stays at 1 and all later changes go through the fade.
			Audio->FadeIn(0.f, WaitingVolume);
		}
		StemAudio.Add(Audio);
	}

	GetWorld()->GetSubsystem<URestorationSubsystem>()->OnMilestoneReached.AddDynamic(this, &UAdaptiveMusicComponent::HandleMilestoneReached);

	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->OnLevelCompleted.AddDynamic(this, &UAdaptiveMusicComponent::PlayFinale);
	}

	FadeInStem(0);
}

void UAdaptiveMusicComponent::HandleMilestoneReached(int32 MilestoneIndex)
{
	// Stem 0 is already playing, so milestone 0 brings in stem 1.
	FadeInStem(MilestoneIndex + 1);
}

void UAdaptiveMusicComponent::FadeInStem(int32 StemIndex)
{
	// FinaleAudio check: a late milestone must not bring a stem back over the finale.
	if (!FinaleAudio && StemAudio.IsValidIndex(StemIndex) && StemAudio[StemIndex])
	{
		UE_LOG(LogTemp, Log, TEXT("Music: stem %d fading in"), StemIndex);
		StemAudio[StemIndex]->AdjustVolume(StemFadeTime, StemVolume);
	}
}

void UAdaptiveMusicComponent::PlayFinale()
{
	if (FinaleAudio || !FinaleTrack)
	{
		return;
	}

	FinaleAudio = UGameplayStatics::CreateSound2D(this, FinaleTrack, 1.f, 1.f, 0.f, nullptr, false, false);
	if (!FinaleAudio)
	{
		return; // Audio is disabled, so there are no stems to fade either.
	}
	FinaleAudio->FadeIn(FinaleFadeTime, StemVolume);

	for (UAudioComponent* Audio : StemAudio)
	{
		if (Audio)
		{
			Audio->FadeOut(FinaleFadeTime, 0.f);
		}
	}
}
