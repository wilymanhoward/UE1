// Last Seed - a door opened by pressure plates.
//
// Purpose: opens smoothly while ALL of its plates are pressed and closes again if any is released, which
// is what makes the two-plate puzzle work.
// Design pattern: observer. The gate subscribes to its plates' events and never polls them.
// Connections: list the plates in RequiredPlates on the placed gate. Listens to APressurePlate.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "Gate.generated.h"

class APressurePlate;
class UCurveFloat;
class UStaticMeshComponent;
class UTimelineComponent;

UCLASS()
class ASSIGNMENT1_API AGate : public AActor
{
	GENERATED_BODY()

public:
	AGate();

protected:
	virtual void BeginPlay() override;

	/** Stays still while the door moves. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	/** The moving door. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Door;

	/** Plays the open and close motion. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UTimelineComponent> OpenTimeline;

	/** All of these must be pressed to open the gate. Set this on the placed gate. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Gate")
	TArray<TObjectPtr<APressurePlate>> RequiredPlates;

	/** Optional motion: time in seconds to door position, 0 closed to 1 open. Empty uses a smooth default. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Gate")
	TObjectPtr<UCurveFloat> OpenCurve;

	/** How far the door moves when fully open, in cm, relative to the actor. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FVector OpenOffset = FVector(0.f, 0.f, 320.f);

	/** Seconds to open when no Open Curve is assigned. An assigned curve sets its own timing. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float DefaultOpenDuration = 1.f;

private:
	// UFUNCTION is required because the timeline and the plate events are dynamic delegates.
	UFUNCTION()
	void HandleOpenProgress(float Alpha);

	UFUNCTION()
	void RefreshGate();

	UCurveFloat* CreateDefaultCurve();
};
