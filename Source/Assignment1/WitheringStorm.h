// Last Seed - the rising storm that chases the player up Storm Ascent.
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

	/** Stops the storm for good. Phase 7 calls this when the level is complete. */
	UFUNCTION(BlueprintCallable, Category = "Storm")
	void StopRising();

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

private:
	UFUNCTION()
	void HandleNoteCollected(FVector Location);

	UFUNCTION()
	void HandleCheckpointSet(FVector Location);

	UFUNCTION()
	void HandleBallRespawned();

	void SetStormZ(float NewZ);
	void UpdateCloseEffects(float DeltaSeconds);

	UPROPERTY(Transient)
	TObjectPtr<ASeedBall> TargetBall;

	bool bRising = false;
	float StartZ = 0.f;
	float SavedZ = 0.f;
	float ShakeTimeRemaining = 0.f;
};
