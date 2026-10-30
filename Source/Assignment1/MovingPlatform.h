// Last Seed - a platform that follows a path.
//
// Purpose: moves along a spline, ping-ponging or looping, with an optional wait at the ends. Two spline
// points make a simple A-to-B platform, and more points make a curved route.
// Design pattern: none.
// Connections: none. The ball rides it through physics friction.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "MovingPlatform.generated.h"

class USplineComponent;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API AMovingPlatform : public AActor
{
	GENERATED_BODY()

public:
	AMovingPlatform();

	virtual void Tick(float DeltaSeconds) override;
	virtual void OnConstruction(const FTransform& Transform) override;

protected:
	/** The route. Select a point in the viewport to move it, and Alt+drag a point to add one. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USplineComponent> Path;

	/** The surface the ball rides. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Off: goes back and forth along the path. On: closes the path into a loop and keeps going round. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	bool bLoop = false;

	/** Travel speed in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float Speed = 200.f;

	/** Seconds to wait at each end of the path, or at the start of each lap when looping. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float WaitTime = 1.f;

private:
	float DistanceAlongPath = 0.f;
	float Direction = 1.f;
	float WaitRemaining = 0.f;
};
