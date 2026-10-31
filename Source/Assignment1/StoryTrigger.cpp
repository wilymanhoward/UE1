// See StoryTrigger.h for this class's purpose and connections.

#include "StoryTrigger.h"

#include "Engine/World.h"
#include "LevelSequence.h"
#include "LSPlayerController.h"
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
	Play();
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
		PlayerController->PlayStory(Sequence, Cards);
	}
}
