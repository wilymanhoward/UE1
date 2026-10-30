// Last Seed - a flower, patch of grass or prop that grows back.
//
// Purpose: invisible until the world recovers enough, or until a note is collected nearby. It then grows
// from nothing with a small bounce, and stays grown even if restoration is later drained.
// Design pattern: observer. It listens to URestorationSubsystem, so collecting a note needs no list of plants.
// Connections: listens to OnRestorationChanged and OnNoteCollected on URestorationSubsystem.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "RestorableActor.generated.h"

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

private:
	UFUNCTION()
	void HandleRestorationChanged(float Restoration);

	UFUNCTION()
	void HandleNoteCollected(FVector Location);

	void StartGrowing();

	FVector FullScale = FVector::OneVector;
	float GrowElapsed = 0.f;
	bool bGrowing = false;
	bool bGrown = false;
};
