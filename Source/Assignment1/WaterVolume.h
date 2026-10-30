// Last Seed - a body of water.
//
// Purpose: slows the ball down, and floats forms with bBuoyancyEnabled, so Stone sinks and rolls along the bottom.
// Design pattern: data-driven. The form's data decides whether it floats.
// Connections: child of ALSVolumeBase. Pushes ASeedBall through AddExternalAcceleration.
// The surface is the top of the box. The box is invisible, so add a water mesh at that height.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "WaterVolume.generated.h"

UCLASS()
class ASSIGNMENT1_API AWaterVolume : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	AWaterVolume();

	virtual void Tick(float DeltaSeconds) override;

protected:
	/** Upward acceleration in cm/s^2 at full buoyancy. It must beat gravity (980) for a form to float. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float BuoyancyAcceleration = 2000.f;

	/** Depth in cm of the ball's centre at which buoyancy reaches full strength. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "1"))
	float BuoyancyDepth = 60.f;

	/** Drag: fraction of speed removed per second. Higher is thicker water, and sinking is slower. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float WaterDrag = 2.5f;
};
