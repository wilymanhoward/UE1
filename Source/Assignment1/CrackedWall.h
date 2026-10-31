// Last Seed - a wall only the Stone Shell can smash.
//
// Purpose: blocks the path until Stone hits it fast enough or slams it. It then hides its mesh and throws
// physics debris, which cleans itself up.
// Design pattern: none. It reacts to the ball through ILSInteractable.
// Connections: ASeedBall calls OnBallHit, passing the velocity from just before the impact.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInteractable.h"
#include "CrackedWall.generated.h"

class USoundBase;
class UStaticMesh;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ACrackedWall : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	ACrackedWall();

	virtual void OnBallHit(ASeedBall* Ball, FVector ImpactVelocity) override;

protected:
	/** Spawn dust here. */
	UFUNCTION(BlueprintImplementableEvent, Category = "Cracked Wall|Effects")
	void PlayBreakEffect();

	/** The solid wall. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Mesh;

	/** Mesh used for each piece of debris. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cracked Wall")
	TObjectPtr<UStaticMesh> DebrisMesh;

	/** Scenery that makes up the blockage, such as a rock pile. It disappears along with the wall's own mesh. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cracked Wall")
	TArray<TObjectPtr<AActor>> RubbleActors;

	/** Plays when the wall breaks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Cracked Wall")
	TObjectPtr<USoundBase> BreakSound;

	/** Impact speed in cm/s Stone needs to break the wall. Stone's default top rolling speed is about 366. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float BreakSpeed = 280.f;

	/** How many pieces of debris to spawn. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	int32 DebrisCount = 10;

	/** Scale applied to each piece of debris. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.01"))
	float DebrisScale = 0.35f;

	/** Mass of each piece in kg. Kept low so debris doesn't stop the ball. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float DebrisMassKg = 5.f;

	/** Launch speed of each piece in cm/s. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float DebrisSpeed = 600.f;

	/** Seconds until the debris and the wall actor are removed. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0.1"))
	float DebrisLifetime = 5.f;

private:
	void Break(const FVector& ImpactVelocity);
	void SpawnDebrisChunk(const FBox& WallBounds, const FVector& ImpactDirection);

	bool bBroken = false;
};
