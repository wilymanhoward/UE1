// Last Seed - data that survives level changes.
//
// Purpose: a game instance lives for the whole play session, so unlocked forms set in Level 1 are still
// there in Level 2. It also saves that data to disk through ULSSaveGame and loads it at startup.
// Phase 7 adds best scores and volume settings.
// Design pattern: none (a plain persistent data holder).
// Connections: ASeedBall asks IsFormUnlocked before switching. AFormFlower calls UnlockForm and
// ACheckpointShrine calls SetLastCheckpoint, then both call SaveProgress.
// Selected in Config/DefaultEngine.ini through GameInstanceClass.

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "SeedFormTypes.h"
#include "LSGameInstance.generated.h"

UCLASS()
class ASSIGNMENT1_API ULSGameInstance : public UGameInstance
{
	GENERATED_BODY()

public:
	/** Runs once when the game starts, before any level loads. */
	virtual void Init() override;

	/** Writes the current progress to disk. */
	UFUNCTION(BlueprintCallable, Category = "Save")
	void SaveProgress();

	/** Deletes the save file and returns to a fresh start with only Seed unlocked. */
	UFUNCTION(BlueprintCallable, Category = "Save")
	void DeleteProgress();

	/** Records the last shrine reached. Call SaveProgress afterward to write it to disk. */
	void SetLastCheckpoint(const FString& LevelName, const FVector& Location);

	UFUNCTION(BlueprintPure, Category = "Forms")
	bool IsFormUnlocked(ESeedForm Form) const { return UnlockedForms.Contains(Form); }

	UFUNCTION(BlueprintCallable, Category = "Forms")
	void UnlockForm(ESeedForm Form) { UnlockedForms.Add(Form); }

	UFUNCTION(BlueprintCallable, Category = "Forms")
	void UnlockAllForms();

protected:
	/** Forms the player may switch to. Seed is always available. */
	UPROPERTY(BlueprintReadOnly, Category = "Forms")
	TSet<ESeedForm> UnlockedForms = { ESeedForm::Seed };

	/** Level of the last shrine reached. Empty if none has been reached. */
	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FString LastLevelName;

	/** Respawn location of the last shrine reached. */
	UPROPERTY(BlueprintReadOnly, Category = "Save")
	FVector LastCheckpointLocation = FVector::ZeroVector;

private:
	void LoadProgress();
};
