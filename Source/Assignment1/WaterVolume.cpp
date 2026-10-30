// See WaterVolume.h for this class's purpose, pattern and connections.

#include "WaterVolume.h"

#include "Components/BoxComponent.h"
#include "SeedBall.h"

AWaterVolume::AWaterVolume()
{
	PrimaryActorTick.bCanEverTick = true;
}

void AWaterVolume::Tick(float DeltaSeconds)
{
	Super::Tick(DeltaSeconds);

	ASeedBall* Ball = GetBallInside();
	if (!Ball)
	{
		return;
	}

	// Drag opposes the current velocity, so the faster the ball moves the harder the water resists.
	FVector Acceleration = -Ball->GetVelocity() * WaterDrag;

	if (Ball->GetCurrentFormData().bBuoyancyEnabled)
	{
		// Buoyancy grows with depth. The ball settles where this balances gravity, and drag stops it bobbing forever.
		const float SurfaceZ = Box->Bounds.GetBox().Max.Z;
		const float Depth = SurfaceZ - Ball->GetActorLocation().Z;
		Acceleration.Z += FMath::Clamp(Depth / BuoyancyDepth, 0.f, 1.f) * BuoyancyAcceleration;
	}

	Ball->AddExternalAcceleration(Acceleration);
}
