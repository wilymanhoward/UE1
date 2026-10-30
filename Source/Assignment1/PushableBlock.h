// Last Seed - a heavy physics block.
//
// Purpose: only Stone pushes it meaningfully, and its mass can hold down a pressure plate. No push code is
// needed: the mass makes the physics engine produce this result. The ball can only push as hard as its own
// grip, which is friction x its weight, so 20 kg Seed can't overcome the friction of a 150 kg block, while
// 80 kg Stone with high-friction PM_Stone can.
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
