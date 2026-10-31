// Last Seed - the rules of a level.
//
// Purpose: selects the default pawn and controller, runs the level timer, counts deaths and petals, works out
// the stars, and runs the level-complete flow: freeze input, optional ending, results, then next level or credits.
// Design pattern: observer. OnLevelCompleted lets other systems react without this class knowing them.
// Connections: spawns ASeedBall and ALSPlayerController. ALevelGoal starts CompleteLevel and supplies the level's
// settings. AGoldenPetal reports here. UAdaptiveMusicComponent and AWitheringStorm listen for completion.
// ULSGameInstance stores the result. Selected in Config/DefaultEngine.ini through GlobalDefaultGameMode. A
// Blueprint child replaces DefaultPawnClass with BP_SeedBall.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/GameModeBase.h"
#include "LSLevelTypes.h"
#include "LSGameMode.generated.h"

class ALevelGoal;
class ALSPlayerController;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnLevelCompleted);

UCLASS()
class ASSIGNMENT1_API ALSGameMode : public AGameModeBase
{
	GENERATED_BODY()

public:
	ALSGameMode();

	virtual void Tick(float DeltaSeconds) override;

	/** The engine calls this to spawn the player's pawn, which is the moment to start listening to it. */
	virtual void RestartPlayer(AController* NewPlayer) override;

	void AddGoldenPetal();

	UFUNCTION(BlueprintPure, Category = "Level")
	int32 GetGoldenPetalsCollected() const { return GoldenPetalsCollected; }

	UFUNCTION(BlueprintPure, Category = "Level")
	int32 GetGoldenPetalsTotal() const { return GoldenPetalsTotal; }

	/** Seconds played so far. Pauses, story cards and cutscenes don't count. */
	UFUNCTION(BlueprintPure, Category = "Level")
	float GetLevelTime() const { return LevelTime; }

	/** True in the main menu level, where the controller shows the menu and not the HUD. */
	bool IsMenuLevel() const { return bMenuLevel; }

	/** Stops or restarts the timer. The controller calls this around cutscenes. */
	void SetTimerRunning(bool bRunning) { bTimerRunning = bRunning; }

	/** Ends the level with this goal's settings. Does nothing if the level is already complete. */
	void CompleteLevel(ALevelGoal* Goal);

	/** The results screen's Next button: goes to the next level, or to the credits after the last level. */
	void ContinueAfterResults();

	/** The results screen's Retry button: reloads this level. */
	void RetryLevel();

	/** Fires once, when the level is complete. */
	UPROPERTY(BlueprintAssignable, Category = "Level")
	FOnLevelCompleted OnLevelCompleted;

protected:
	virtual void BeginPlay() override;

	/** Tick this on a child used only by the main menu level, and set its Default Pawn Class to None. */
	UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "Level")
	bool bMenuLevel = false;

private:
	UFUNCTION()
	void HandleBallDied();

	FLSLevelResult BuildResult(const ALevelGoal* Goal) const;
	ALSPlayerController* GetLSPlayerController() const;

	UPROPERTY(Transient)
	TObjectPtr<ALevelGoal> CompletedGoal;

	FLSLevelResult LastResult;
	float LevelTime = 0.f;
	int32 Deaths = 0;
	int32 GoldenPetalsCollected = 0;
	int32 GoldenPetalsTotal = 0;
	bool bTimerRunning = true;
	bool bLevelComplete = false;
};
