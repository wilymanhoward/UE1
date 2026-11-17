// Last Seed - a flower, patch of grass, prop or tree that grows back.
//
// Purpose: invisible until the world recovers enough, or until a note is collected nearby. It then grows
// from nothing with a small bounce, and stays grown even if restoration is later drained. With a Withered Mesh
// set, it shows that instead until then (a dead trunk where a tree will grow), which shrinks away as it grows.
// Trees also wait a random moment, sway as they grow (ShakeDegrees) and play GrowSound when they start.
// Design pattern: observer. It listens to URestorationSubsystem, so collecting a note needs no list of plants.
// Connections: listens to OnRestorationChanged and OnNoteCollected on URestorationSubsystem.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RestorableActor.generated.h"

class USoundBase;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ARestorableActor : public AActor
{
	GENERATED_BODY()

public:
	ARestorableActor();

	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

	/** Add a sparkle or a sound here. Fires when growth starts. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Restorable|Effects")
	void PlayGrowEffect();

	/** Stays still while the mesh scales. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	/** The plant or prop. It has no collision by default. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Optional. What stands here before it grows, such as a dead trunk. It shrinks away as Mesh grows. No collision. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> WitheredMesh;

	/** Grows when restoration reaches this value (0 to 1). Above 1 means only a nearby note can trigger it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RestorationThreshold = 0.5f;

	/** Also grows when a note is collected within this many cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float NoteRadius = 800.f;

	/** Seconds to reach full size. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.01"))
	float GrowDuration = 0.6f;

	/** How far it overshoots before settling. 0 has no bounce, and 1.7 goes about 10% past full size. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float BounceAmount = 1.7f;

	/** Waits a random time up to this many seconds before growing, so a stand of trees rises in a wave, not all at once. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float MaxStartDelay = 0.f;

	/** How far it sways while growing, in degrees, fading to nothing as it reaches full size. 0 keeps it still. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Shake", meta = (ClampMin = "0"))
	float ShakeDegrees = 0.f;

	/** Sways per second while growing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning|Shake", meta = (ClampMin = "0"))
	float ShakeFrequency = 3.f;

	/** Played where it stands as it starts to grow. Its own attenuation makes it quieter with distance. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Restorable|Effects")
	TObjectPtr<USoundBase> GrowSound;

private:
	UFUNCTION()
	void HandleRestorationChanged(float Restoration);

	UFUNCTION()
	void HandleNoteCollected(FVector Location);

	void StartGrowing();

	/** The first part of growing, once any start delay has passed: shows the mesh and plays the sound. */
	void BeginGrowth();

	FVector FullScale = FVector::OneVector;
	FVector WitheredScale = FVector::OneVector;
	float GrowElapsed = 0.f;  // Negative while the start delay runs.
	float ShakePhase = 0.f;  // Each one sways out of step with its neighbours.
	bool bGrowthBegun = false;
	bool bGrowing = false;
	bool bGrown = false;
};
