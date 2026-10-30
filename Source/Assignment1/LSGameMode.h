// Last Seed - the rules of a level.
//
// Purpose: selects the default pawn and player controller, and counts the level's Golden Petals.
// Phase 7 adds the level timer, death counter and the rest of the level-complete flow.
// Design pattern: observer. OnLevelCompleted lets other systems react without this class knowing them.
// Connections: spawns ASeedBall and ALSPlayerController. AGoldenPetal reports here. UAdaptiveMusicComponent
// listens for level completion. Selected in Config/DefaultEngine.ini through GlobalDefaultGameMode. A Blueprint
// child replaces DefaultPawnClass with BP_SeedBall.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "LSGameMode.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnLevelCompleted);

UCLASS()
class ASSIGNMENT1_API ALSGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ALSGameMode();

	void AddGoldenPetal();

	UFUNCTION(BlueprintPure, Category = "Level")
	int32 GetGoldenPetalsCollected() const { return GoldenPetalsCollected; }

	/** Ends the level. Does nothing if the level is already complete. */
	UFUNCTION(BlueprintCallable, Category = "Level")
	void CompleteLevel();

	/** Fires once, when the level is complete. */
	UPROPERTY(BlueprintAssignable, Category = "Level")
	FOnLevelCompleted OnLevelCompleted;

private:
	int32 GoldenPetalsCollected = 0;
	bool bLevelComplete = false;
};
