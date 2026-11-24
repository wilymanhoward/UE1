// Last Seed - a one-shot burst of droplets where the ball falls into lava or water.
//
// Purpose: makes a lava death read as a splash. Glowing blobs are thrown up in a crown, fall back under gravity
// and shrink away, while an orange flash lights the spot. It removes itself when done.
// Design pattern: none.
// Connections: spawned by AKillVolume::Burn, which passes the droplet material.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSLavaSplash.generated.h"

class UMaterialInterface;
class UPointLightComponent;
class UStaticMesh;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ALSLavaSplash : public AActor
{
	GENERATED_BODY()

public:
	ALSLavaSplash();

	virtual void Tick(float DeltaSeconds) override;

	/** Spawns the droplets. Call once, right after spawning. */
	void Burst(UMaterialInterface* DropletMaterial, float Size);
	void Burst(UMaterialInterface* DropletMaterial, float Size, bool bWater);

private:
	UPROPERTY(VisibleAnywhere, Category = "Components")
	TObjectPtr<UPointLightComponent> Flash;

	UPROPERTY(Transient)
	TObjectPtr<UStaticMesh> DropletMesh;

	UPROPERTY()
	TObjectPtr<UMaterialInterface> WaterDropletMaterial;

	UPROPERTY(Transient)
	TArray<TObjectPtr<UStaticMeshComponent>> Droplets;

	TArray<FVector> Velocities;
	TArray<float> BaseScales;
	float Age = 0.f;
	float Lifetime = 1.4f;
	float FlashIntensity = 0.f;
};
