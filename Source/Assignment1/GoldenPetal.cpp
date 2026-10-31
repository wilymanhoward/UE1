// See GoldenPetal.h for this class's purpose, pattern and connections.

#include "GoldenPetal.h"

#include "Engine/World.h"
#include "LSGameMode.h"

AGoldenPetal::AGoldenPetal()
{
#if WITH_EDITORONLY_DATA
	// World Partition only loads actors near the player, and the petal total must include the whole level.
	bIsSpatiallyLoaded = false;
#endif
}

void AGoldenPetal::OnCollected(ASeedBall* Ball)
{
	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->AddGoldenPetal();
	}
}
