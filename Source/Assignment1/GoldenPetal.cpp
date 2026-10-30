// See GoldenPetal.h for this class's purpose, pattern and connections.

#include "GoldenPetal.h"

#include "Engine/World.h"
#include "LSGameMode.h"

void AGoldenPetal::OnCollected(ASeedBall* Ball)
{
	if (ALSGameMode* GameMode = GetWorld()->GetAuthGameMode<ALSGameMode>())
	{
		GameMode->AddGoldenPetal();
	}
}
