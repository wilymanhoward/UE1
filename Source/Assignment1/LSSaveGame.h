// Last Seed - the data written to disk.
//
// Purpose: holds the fields of a save file: unlocked forms, best scores per level, and volume settings.
// Design pattern: memento. It is a snapshot of ULSGameInstance's state, with no logic of its own.
// Connections: created and read only by ULSGameInstance.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
#include "LSLevelTypes.h"
#include "SeedFormTypes.h"
#include "LSSaveGame.generated.h"

UCLASS()
class ASSIGNMENT1_API ULSSaveGame : public USaveGame
{
	GENERATED_BODY()

public:
	/** Forms the player has unlocked. */
	UPROPERTY()
	TSet<ESeedForm> UnlockedForms;

	/** Best scores, by level name. A level is in this map once it has been finished. */
	UPROPERTY()
	TMap<FName, FLSLevelRecord> LevelRecords;

	/** Music volume from 0 to 1. */
	UPROPERTY()
	float MusicVolume = 1.f;

	/** Sound effect volume from 0 to 1. */
	UPROPERTY()
	float SfxVolume = 1.f;
};
