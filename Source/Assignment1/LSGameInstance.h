// Last Seed - data that survives level changes.
//
// Purpose: a game instance lives for the whole play session, so unlocked forms set in Level 1 are still
// there in Level 2. It holds forms, best scores and volume settings, saves them to disk through ULSSaveGame,
// and loads them at startup.
// Design pattern: none (a plain persistent data holder).
// Connections: ASeedBall asks IsFormUnlocked before switching. AFormFlower calls UnlockForm then SaveProgress.
// ALSGameMode calls RecordLevelResult. ULSMainMenuWidget reads the records and ULSPauseMenuWidget sets the
// volumes. Selected in Config/DefaultEngine.ini through GameInstanceClass.

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "LSLevelTypes.h"
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

	UFUNCTION(BlueprintPure, Category = "Forms")
	bool IsFormUnlocked(ESeedForm Form) const { return UnlockedForms.Contains(Form); }

	UFUNCTION(BlueprintCallable, Category = "Forms")
	void UnlockForm(ESeedForm Form) { UnlockedForms.Add(Form); }

	UFUNCTION(BlueprintCallable, Category = "Forms")
	void UnlockAllForms();

	/** A new run of Level 1: only Seed until its flowers are found again. Whatever they unlock carries into Level 2.
	 *  The save file keeps every form ever unlocked (SaveProgress merges), so Level 2 opened from the menu has them. */
	void ResetFormsForNewRun() { UnlockedForms = { ESeedForm::Seed }; }

	/** Keeps the best of this run and any earlier runs, then saves. */
	void RecordLevelResult(FName LevelName, const FLSLevelResult& Result);

	/** True once the level has been finished at least once. */
	UFUNCTION(BlueprintPure, Category = "Progress")
	bool IsLevelFinished(FName LevelName) const { return LevelRecords.Contains(LevelName); }

	/** The level's best scores. All zero if it hasn't been finished. */
	UFUNCTION(BlueprintPure, Category = "Progress")
	FLSLevelRecord GetLevelRecord(FName LevelName) const { return LevelRecords.FindRef(LevelName); }

	/** Adds up the best petal count of every level. */
	UFUNCTION(BlueprintPure, Category = "Progress")
	int32 GetTotalPetals() const;

	/** Set by Emberwood's energy burst, so the next level opens fully restored. Read once by ALSGameMode::InitGame. Not saved. */
	bool bRestoredArrival = false;

	float GetMusicVolume() const { return MusicVolume; }
	float GetSfxVolume() const { return SfxVolume; }
	void SetMusicVolume(float Volume) { MusicVolume = Volume; }
	void SetSfxVolume(float Volume) { SfxVolume = Volume; }

protected:
	/** Forms the player may switch to. Seed is always available. */
	UPROPERTY(BlueprintReadOnly, Category = "Forms")
	TSet<ESeedForm> UnlockedForms = { ESeedForm::Seed };

	/** Best scores, by level name. */
	UPROPERTY(BlueprintReadOnly, Category = "Progress")
	TMap<FName, FLSLevelRecord> LevelRecords;

	/** Music volume from 0 to 1. */
	UPROPERTY(BlueprintReadOnly, Category = "Audio")
	float MusicVolume = 1.f;

	/** Sound effect volume from 0 to 1. */
	UPROPERTY(BlueprintReadOnly, Category = "Audio")
	float SfxVolume = 1.f;

private:
	void LoadProgress();
};
