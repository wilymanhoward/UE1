// Last Seed - the storm that chases the player: rising up Storm Ascent, or along a trail (ChasePoints).
//
// Purpose: once triggered, a huge kill box rises at a set speed. Each collected note pushes it back down.
// Touching it kills the ball. After a respawn it returns to a position saved at the last checkpoint. As it
// gets close, it shakes the camera and raises a rumble's volume.
// Design pattern: observer. It listens to URestorationSubsystem for notes, and ASeedBall for checkpoints
// and respawns, and neither of them knows the storm exists.
// Connections: started by AStormTrigger. Child of ALSVolumeBase.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "WitheringStorm.generated.h"

class ASeedBall;
class UAudioComponent;
class UCameraShakeBase;
class UStaticMeshComponent;
class ARestorableActor;

UCLASS()
class ASSIGNMENT1_API AWitheringStorm : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	AWitheringStorm();

	virtual void Tick(float DeltaSeconds) override;

	/** Starts the storm and remembers the ball. Does nothing if the storm has already started. */
	UFUNCTION(BlueprintCallable, Category = "Storm")
	void StartRising(ASeedBall* Ball);

	/** Stops the storm for good. Runs when ALSGameMode reports that the level is complete. */
	UFUNCTION(BlueprintCallable, Category = "Storm")
	void StopRising();
	UPROPERTY(EditAnywhere, Category = "Storm")
	TArray<TObjectPtr<ARestorableActor>> CurseTrees;
	UPROPERTY(EditAnywhere, Category = "Storm")
	float StartDelay = 0.f;
	UPROPERTY(EditAnywhere, Category = "Storm")
	bool bShockwaveAttacks = false;
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UAudioComponent> AttackAudio;

protected:
	virtual void BeginPlay() override;

	/** The visible storm wall. Assign a dark, swirling translucent material. It has no collision. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Plays while rising, and gets louder as the storm nears the ball. Assign a looping sound. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UAudioComponent> RumbleAudio;

	/** Camera shake played while the storm is close. Optional. Its duration should be at least Shake Interval. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	TSubclassOf<UCameraShakeBase> CloseShake;

	/** Rising speed in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RiseSpeed = 120.f;

	/** How far each collected note pushes the storm down, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float NotePushback = 300.f;

	/** The storm stops after rising this far from its start, in cm. Keep it below the level's goal. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float MaxRiseDistance = 20000.f;

	/** Minimum gap in cm kept between the storm's top and a checkpoint, so a respawn is never instantly fatal. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RespawnClearance = 800.f;

	/** The shake and rumble start when the storm's top is this close to the ball, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "1"))
	float CloseDistance = 1500.f;

	/** Seconds between camera shakes while the storm is close. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float ShakeInterval = 1.f;

	/** Optional. World points along a trail, in order. With two or more, the storm chases along them instead of
	 *  rising: it faces down the path, its front (the box's +X face) moves at Rise Speed, notes push it back along
	 *  the path, and Max Rise Distance limits how far it goes. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Storm")
	TArray<FVector> ChasePoints;

private:
	UFUNCTION()
	void HandleNoteCollected(FVector Location);

	UFUNCTION()
	void HandleCheckpointSet(FVector Location);

	UFUNCTION()
	void HandleBallRespawned();

	void SetStormZ(float NewZ);
	void UpdateCloseEffects(float DeltaSeconds);

	// The chase along ChasePoints. Progress is the distance along the path of the storm's middle.
	bool FollowsPath() const { return ChasePoints.Num() >= 2; }
	void SetProgress(float NewProgress);
	float PathDistanceOf(const FVector& Location) const;
	float GetPathLength() const;
	float Progress = 0.f;
	float SavedProgress = 0.f;
	/** Along a path: whether the ball has reached a checkpoint since the chase began. */
	bool bCheckpointInChase = false;

	/** The ball being chased. Set when the storm starts. */
	UPROPERTY(Transient)
	TObjectPtr<ASeedBall> TargetBall;

	bool bRising = false;
	float StartZ = 0.f;
	float SavedZ = 0.f;
	float ShakeTimeRemaining = 0.f;
	float DelayRemaining = 0.f;
	void TickShockwave(float DeltaSeconds);
	bool bWaveActive = false;
	int32 HeightTier = -1;
	float WaveHeight = 25.f;
};
