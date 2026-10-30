// Last Seed - the data written to disk.
//
// Purpose: holds the fields of a save file. Phase 7 adds best stars, times, petals and volume settings.
// Design pattern: memento. It is a snapshot of ULSGameInstance's state, with no logic of its own.
// Connections: created and read only by ULSGameInstance.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/SaveGame.h"
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

	/** Name of the level containing the last activated shrine. */
	UPROPERTY()
	FString LastLevelName;

	/** Respawn location of the last activated shrine. */
	UPROPERTY()
	FVector LastCheckpointLocation = FVector::ZeroVector;
};
