// Last Seed - the rules of a level.
//
// Purpose: selects the default pawn and player controller, and counts the level's Golden Petals.
// Phase 7 adds the level timer, death counter and level-complete flow.
// Design pattern: none yet.
// Connections: spawns ASeedBall and ALSPlayerController. AGoldenPetal reports here. Selected in
// Config/DefaultEngine.ini through GlobalDefaultGameMode. A Blueprint child replaces DefaultPawnClass
// with BP_SeedBall.

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

	void AddGoldenPetal();

	UFUNCTION(BlueprintPure, Category = "Level")
	int32 GetGoldenPetalsCollected() const { return GoldenPetalsCollected; }

private:
	int32 GoldenPetalsCollected = 0;
};
