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

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	float TimeSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	float ParTimeSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 Deaths = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 NotesCollected = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 NotesTotal = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 PetalsCollected = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 PetalsTotal = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	int32 PetalsRequired = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	bool bAllNotes = false;

	UPROPERTY(BlueprintReadOnly, Category = "Result")
	bool bUnderPar = false;

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

	UPROPERTY(BlueprintReadOnly, Category = "Record")
	int32 BestStars = 0;

	UPROPERTY(BlueprintReadOnly, Category = "Record")
	float BestTimeSeconds = 0.f;

	UPROPERTY(BlueprintReadOnly, Category = "Record")
	int32 BestPetals = 0;
};

/** Formats seconds as minutes and seconds, such as 4:07. */
inline FText LSFormatTime(float Seconds)
{
	const int32 WholeSeconds = FMath::FloorToInt(Seconds);
	return FText::FromString(FString::Printf(TEXT("%d:%02d"), WholeSeconds / 60, WholeSeconds % 60));
}
