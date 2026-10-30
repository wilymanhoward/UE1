// Last Seed - the single source of truth for how restored the world is.
//
// Purpose: counts Life Notes, works out Restoration from 0 to 1, applies Wither Blob drain, and locks in
// progress at checkpoints. It holds rules only. Everything visible reacts to its events.
// Design patterns:
//   - Subsystem: one instance per world, created by the engine, reachable from anywhere with GetSubsystem.
//   - Observer: OnRestorationChanged, OnMilestoneReached and OnNoteCollected mean this class never needs
//     to know about materials, plants, music or the HUD.
// Connections: ALifeNote reports to it. ACheckpointShrine locks progress. ARestorationDriver and
// ARestorableActor listen. AWitherBlob (Phase 5) drains it, and the adaptive music (Phase 6) listens for milestones.

#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "RestorationSubsystem.generated.h"

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnRestorationChanged, float, Restoration);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnRestorationMilestone, int32, MilestoneIndex);
DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FOnNoteCollected, FVector, Location);

UCLASS()
class ASSIGNMENT1_API URestorationSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	/** Counts the Life Notes in the level. The engine calls this once when play starts. */
	virtual void OnWorldBeginPlay(UWorld& InWorld) override;

	/** Limits this to real play. Without it, one would also exist for every editor preview world. */
	virtual bool DoesSupportWorldType(const EWorldType::Type WorldType) const override;

	/** Called by ALifeNote when it is collected. */
	UFUNCTION(BlueprintCallable, Category = "Restoration")
	void ReportNoteCollected(const FVector& Location);

	/** Lowers restoration by Amount (0 to 1), but never below what checkpoints have locked in. */
	UFUNCTION(BlueprintCallable, Category = "Restoration")
	void DrainRestoration(float Amount);

	/** Called by ACheckpointShrine. Drain can no longer take restoration below its current value. */
	UFUNCTION(BlueprintCallable, Category = "Restoration")
	void LockInRestoration();

	UFUNCTION(BlueprintPure, Category = "Restoration")
	float GetRestoration() const { return Restoration; }

	UFUNCTION(BlueprintPure, Category = "Restoration")
	int32 GetNotesCollected() const { return NotesCollected; }

	UFUNCTION(BlueprintPure, Category = "Restoration")
	int32 GetNotesTotal() const { return NotesTotal; }

	/** Fires whenever Restoration changes, with the new value. */
	UPROPERTY(BlueprintAssignable, Category = "Restoration")
	FOnRestorationChanged OnRestorationChanged;

	/** Fires once each at 25, 50, 75 and 100 percent, with index 0 to 3. Drain does not make one fire again. */
	UPROPERTY(BlueprintAssignable, Category = "Restoration")
	FOnRestorationMilestone OnMilestoneReached;

	/** Fires when a note is collected, with its location. */
	UPROPERTY(BlueprintAssignable, Category = "Restoration")
	FOnNoteCollected OnNoteCollected;

private:
	float GetNoteFraction() const;
	void SetRestoration(float NewRestoration);
	void BroadcastNewMilestones();

	int32 NotesCollected = 0;
	int32 NotesTotal = 0;
	float Restoration = 0.f;
	// Drain taken so far. Restoration is worked out from the note count minus this, so rounding never builds up.
	float DrainPenalty = 0.f;
	float LockedRestoration = 0.f;
	int32 NextMilestone = 0;
};
