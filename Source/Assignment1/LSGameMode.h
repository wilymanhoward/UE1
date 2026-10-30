// Last Seed - the rules of a level.
//
// Purpose: for now it only selects the default pawn and player controller. Phase 7 adds the level timer,
// death counter and level-complete flow.
// Design pattern: none yet.
// Connections: spawns ASeedBall and ALSPlayerController. Selected in Config/DefaultEngine.ini through
// GlobalDefaultGameMode. A Blueprint child replaces DefaultPawnClass with BP_SeedBall.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "LSGameMode.generated.h"

UCLASS()
class ASSIGNMENT1_API ALSGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ALSGameMode();
};
