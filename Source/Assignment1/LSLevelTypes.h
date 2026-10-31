// Last Seed - shared level score types.
//
// Purpose: FLSLevelResult describes one finished run, and FLSLevelRecord is the best the player has done.
// Design pattern: none. These are plain data.
// Connections: ALSGameMode fills a result. ULSResultsWidget shows it. ULSGameInstance turns it into a record,
// and ULSSaveGame writes the records to disk.

#pragma once

#include "CoreMinimal.h"
#include "LSLevelTypes.generated.h"

/** One finished run of a level, with each star condition recorded so the results screen can show it. */
USTRUCT(BlueprintType)
struct FLSLevelResult
{
	GENERATED_BODY()

	/** Time taken, in seconds. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	float TimeSeconds = 0.f;

	/** Time to beat for the third star, in seconds. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	float ParTimeSeconds = 0.f;

	/** Times the ball died. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 Deaths = 0;

	/** Life Notes collected. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 NotesCollected = 0;

	/** Life Notes in the level. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 NotesTotal = 0;

	/** Golden Petals collected. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 PetalsCollected = 0;

	/** Golden Petals in the level. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 PetalsTotal = 0;

	/** Golden Petals needed for the third star. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 PetalsRequired = 0;

	/** True if every Life Note was collected. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	bool bAllNotes = false;

	/** True if the time beat the par time. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	bool bUnderPar = false;

	/** True if enough Golden Petals were collected. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	bool bEnoughPetals = false;

	/** 1 to 3. */
	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 Stars = 1;
};

/** The best values for one level across all runs. Each value can come from a different run. */
USTRUCT(BlueprintType)
struct FLSLevelRecord
{
	GENERATED_BODY()

	/** Most stars earned. */
	UPROPERTY(BlueprintReadOnly, Category = "Record")
	int32 BestStars = 0;

	/** Fastest time, in seconds. */
	UPROPERTY(BlueprintReadOnly, Category = "Record")
	float BestTimeSeconds = 0.f;

	/** Most Golden Petals collected in one run. */
	UPROPERTY(BlueprintReadOnly, Category = "Record")
	int32 BestPetals = 0;
};

/** Formats seconds as minutes and seconds, such as 4:07. */
inline FText LSFormatTime(float Seconds)
{
	const int32 WholeSeconds = FMath::FloorToInt(Seconds);
	return FText::FromString(FString::Printf(TEXT("%d:%02d"), WholeSeconds / 60, WholeSeconds % 60));
}
