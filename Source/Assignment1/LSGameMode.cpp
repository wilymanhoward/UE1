// See LSGameMode.h for this class's purpose and connections.

#include "LSGameMode.h"

#include "LSPlayerController.h"
#include "SeedBall.h"

ALSGameMode::ALSGameMode()
{
	DefaultPawnClass = ASeedBall::StaticClass();
	PlayerControllerClass = ALSPlayerController::StaticClass();
}

void ALSGameMode::AddGoldenPetal()
{
	++GoldenPetalsCollected;
	UE_LOG(LogTemp, Log, TEXT("Golden Petals collected: %d"), GoldenPetalsCollected);
}
