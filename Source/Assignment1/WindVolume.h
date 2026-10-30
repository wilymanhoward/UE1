// Last Seed - a box of wind.
//
// Purpose: pushes the ball while it is inside, scaled by the form's WindResponse, so Dandelion is blown
// around and Stone barely moves. An updraft is a wind volume pointing up. It can pulse on a timer, and can
// be powered by a pressure plate for the fan puzzle.
// Design pattern: data-driven. The form's data decides how strongly the wind affects it.
// Connections: child of ALSVolumeBase. Pushes ASeedBall through AddExternalAcceleration. Reads
// APressurePlate::IsPressed. ASteamVent is a child with different defaults.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "WindVolume.generated.h"

class APressurePlate;
class UArrowComponent;
class UNiagaraComponent;

UCLASS()
class ASSIGNMENT1_API AWindVolume : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	AWindVolume();

	virtual void Tick(float DeltaSeconds) override;
	virtual void OnConstruction(const FTransform& Transform) override;

	/** True while the wind is blowing, after the power plate and the pulse timer are taken into account. */
	UFUNCTION(BlueprintPure, Category = "Wind")
	bool IsWindActive() const;

protected:
	/** Fires when the wind turns on or off. Use it for sound, or for effects beyond the Particles component. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Wind|Effects")
	void PlayWindActiveEffect(bool bActive);

	/** Assign a Niagara system to this component. It plays only while the wind is on. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UNiagaraComponent> Particles;

	/** Shows the wind direction in the editor only. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UArrowComponent> DirectionArrow;

	/** Optional. When set, the wind only blows while this plate is pressed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Wind")
	TObjectPtr<APressurePlate> PowerPlate;

	/** Direction the wind blows in world space. (0, 0, 1) makes an updraft. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	FVector WindDirection = FVector(1.f, 0.f, 0.f);

	/** Acceleration in cm/s^2 before WindResponse. Gravity is 980, so an updraft needs more than that to lift Seed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float Strength = 1500.f;

	/** Turns the wind on and off on a repeating timer. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	bool bPulsing = false;

	/** Seconds on, per pulse. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float PulseOnTime = 2.f;

	/** Seconds off, per pulse. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float PulseOffTime = 2.f;

	/** Seconds to shift this volume's pulse, so neighbouring volumes can take turns. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float PulseOffset = 0.f;

private:
	bool bWasActive = false;
};
