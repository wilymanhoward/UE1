// See StoryTrigger.h for this class's purpose and connections.

#include "StoryTrigger.h"

#include "Engine/World.h"
#include "LevelSequence.h"
#include "LSPlayerController.h"
#include "SeedBall.h"
#include "TimerManager.h"

AStoryTrigger::AStoryTrigger()
{
#if WITH_EDITORONLY_DATA
	// A Play On Start trigger can be anywhere, and World Partition might not have loaded it at the start.
	bIsSpatiallyLoaded = false;
#endif
}

void AStoryTrigger::BeginPlay()
{
	Super::BeginPlay();

	if (bPlayOnStart)
	{
		// Waits one frame, because the controller may not have created its widgets yet.
		GetWorldTimerManager().SetTimerForNextTick(this, &AStoryTrigger::Play);
	}
}

void AStoryTrigger::OnBallOverlap(ASeedBall* Ball)
{
	if (bPlayed || !Ball || Ball->IsDead()) return;
	if (bWaitForLanding)
	{
		if (!GetWorldTimerManager().IsTimerActive(LandingTimer))
			GetWorldTimerManager().SetTimer(LandingTimer, this, &AStoryTrigger::CheckLanding, 0.05f, true);
	}
	else Play();
}

void AStoryTrigger::CheckLanding()
{
	const ASeedBall* Ball = GetBallInside();
	if (Ball && (!Ball->IsGrounded() || Ball->GetVelocity().Z > 40.f)) return;
	GetWorldTimerManager().ClearTimer(LandingTimer);
	if (Ball) Play();
}

void AStoryTrigger::Play()
{
	if (bPlayed)
	{
		return;
	}
	bPlayed = true;

	if (ALSPlayerController* PlayerController = Cast<ALSPlayerController>(GetWorld()->GetFirstPlayerController()))
	{
		if (!IntroShots.IsEmpty())
		{
			const FVector RevealTarget = RevealTargetOffset.IsNearlyZero()
				? FVector::ZeroVector : GetActorLocation() + RevealTargetOffset;
			PlayerController->PlayIntro(IntroShots, IntroMusic, IntroVoiceOver, bPlayOnStart, RevealTarget);
		}
		else
		{
			PlayerController->PlayStory(Sequence, Cards);
		}
	}
}
