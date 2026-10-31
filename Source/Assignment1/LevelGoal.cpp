// See LevelGoal.h for this class's purpose and connections.

#include "LevelGoal.h"

#include "Engine/World.h"
#include "LevelSequence.h"
#include "LSGameMode.h"

ALevelGoal::ALevelGoal()
{
#if WITH_EDITORONLY_DATA
	// World Partition must keep this loaded, because the test command looks for it from anywhere in the level.
	bIsSpatiallyLoaded = false;
#endif
}

void ALevelGoal::OnBallOverlap(ASeedBall* Ball)
{
	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->CompleteLevel(this);
	}
}
