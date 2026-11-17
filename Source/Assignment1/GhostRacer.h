// Last Seed - a ghost of the player's best run to race against.
//
// Purpose: records where the ball is as the level timer runs, and when the level is finished faster than ever
// before, saves that run. On the next attempt a pale glowing ball replays it, so the player races their own best.
// Design pattern: observer (listens to ALSGameMode::OnLevelCompleted). ULSGhostSave is a memento of the run.
// Connections: reads ALSGameMode::GetLevelTime, so the ghost and the player share one clock that stops during
// story cards. The run is kept in its own save slot per level, "Ghost_<level>". Placed by the level build, which
// sets the ghost's material.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "GameFramework/SaveGame.h"
#include "GhostRacer.generated.h"

class ASeedBall;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ULSGhostSave : public USaveGame
{
	GENERATED_BODY()

public:
	/** The finishing time of the run, in seconds of level time. */
	UPROPERTY()
	float TimeSeconds = 0.f;

	/** Where the ball was every SampleInterval seconds of level time. */
	UPROPERTY()
	TArray<FVector> Points;

	UPROPERTY()
	float SampleInterval = 0.1f;
};

UCLASS()
class ASSIGNMENT1_API AGhostRacer : public AActor
{
	GENERATED_BODY()

public:
	AGhostRacer();

	virtual void Tick(float DeltaSeconds) override;

	/** True when there is a best run to race this time. */
	UFUNCTION(BlueprintPure, Category = "Ghost")
	bool HasGhost() const { return Best != nullptr; }

protected:
	virtual void BeginPlay() override;

	/** The ghost ball. Assign a pale, see-through glowing material. It has no collision. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Ghost;

	/** Seconds of level time between recorded points. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.02"))
	float SampleInterval = 0.1f;

	/** Recording stops after this many seconds, so a very long run can't grow the save without end. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "1"))
	float MaxRecordSeconds = 1800.f;

private:
	UFUNCTION()
	void HandleLevelCompleted();

	FString SlotName() const;

	/** The run being raced, or null on a first attempt. */
	UPROPERTY(Transient)
	TObjectPtr<ULSGhostSave> Best;

	UPROPERTY(Transient)
	TObjectPtr<ASeedBall> Ball;

	TArray<FVector> Recording;
	bool bDone = false;
};
