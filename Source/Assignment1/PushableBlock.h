// Last Seed - a heavy physics block.
//
// Purpose: only Stone pushes it meaningfully, and its mass can hold down a pressure plate. No push code is
// needed: the mass makes the physics engine produce this result. A ball pushes with the smaller of its grip
// (friction x weight) and its rolling force (0.4 x mass x radius x TorqueStrength). On PM_Ice floors Seed
// has almost no grip, while PM_Stone gives Stone about 40000 units of push against the 150 kg block's 7350.
// On a normal floor the block's friction is about 103000, so Stone only nudges it. Use about 52 kg there.
// Design pattern: none.
// Connections: APressurePlate counts its mass. Nothing else references it.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "PushableBlock.generated.h"

class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API APushableBlock : public AActor
{
	GENERATED_BODY()

public:
	APushableBlock();

	/** Falling out of the world would destroy the block and make its puzzle impossible, so it goes back to its start. */
	virtual void FellOutOfWorld(const UDamageType& DamageType) override;

protected:
	virtual void BeginPlay() override;

	/** The physics body. Assign a slippery physical material here for ice blocks. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Mass in kg. See the class comment for how this decides which forms can push it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float MassKg = 150.f;

private:
	FTransform StartTransform;
};
