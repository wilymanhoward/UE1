// Last Seed - a floor plate that reacts to weight.
//
// Purpose: pressed while the total mass of the physics bodies on it reaches a threshold, so Stone or a
// pushable block works and the light forms get a "Too light!" prompt.
// Design pattern: observer. Gates and wind volumes listen, and the plate doesn't know who is listening.
// Connections: AGate binds to OnPlatePressed and OnPlateReleased. AWindVolume reads IsPressed. ASeedBall calls
// OnBallOverlap. ALSPlayerController shows the prompt.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInteractable.h"
#include "PressurePlate.generated.h"

class UBoxComponent;
class UStaticMeshComponent;

DECLARE_DYNAMIC_MULTICAST_DELEGATE(FOnPlateChanged);

UCLASS()
class ASSIGNMENT1_API APressurePlate : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	APressurePlate();

	virtual void Tick(float DeltaSeconds) override;
	virtual void OnBallOverlap(ASeedBall* Ball) override;

	UFUNCTION(BlueprintPure, Category = "Pressure Plate")
	bool IsPressed() const { return bPressed; }
	/** Fires when the mass on the plate reaches the threshold. */
	UPROPERTY(BlueprintAssignable, Category = "Pressure Plate")
	FOnPlateChanged OnPlatePressed;

	/** Fires when the mass on the plate drops below the threshold. */
	UPROPERTY(BlueprintAssignable, Category = "Pressure Plate")
	FOnPlateChanged OnPlateReleased;

protected:
	/** Keeps the trigger still while the mesh moves down. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	/** The visible plate, which sinks when pressed. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** The area above the plate where mass is measured. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UBoxComponent> Trigger;

	/** Shown when the ball is on the plate but is not heavy enough. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Pressure Plate")
	FText TooLightMessage;

	/** Mass in kg needed to press the plate. Default forms: Seed 20, Dandelion 5, Stone 80. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float RequiredMassKg = 50.f;

	/** How far the plate sinks when pressed, in cm. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float PressDepth = 8.f;

	/** How fast the plate moves up and down, in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float PressSpeed = 40.f;

	/** Seconds the "too light" message stays on screen. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float PromptDuration = 2.f;

	/** Minimum seconds between "too light" messages, so rolling on and off doesn't spam them. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float PromptCooldown = 3.f;

private:
	float GetMassOnPlate() const;

	bool bPressed = false;
	float CurrentDepth = 0.f;
	double NextPromptTime = 0.0;
};
