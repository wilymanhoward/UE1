// Last Seed - a giant mushroom that bounces the ball high into the air.
//
// Purpose: land on the cap and the ball is thrown upward, keeping its forward speed, while the cap squashes and
// springs back with a boing. Some sit on the trail for fun, some lead to hidden ledges.
// Design pattern: none beyond reacting to the ball through ILSInteractable.
// Connections: ASeedBall calls OnBallHit. Its meshes (Stem, Cap) are set by the level build.

#pragma once

#include "CoreMinimal.h"
#include "GameFramework/Actor.h"
#include "LSInteractable.h"
#include "BounceMushroom.generated.h"

class USoundBase;
class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ABounceMushroom : public AActor, public ILSInteractable
{
	GENERATED_BODY()

public:
	ABounceMushroom();

	virtual void Tick(float DeltaSeconds) override;
	virtual void OnBallHit(ASeedBall* Ball, FVector ImpactVelocity) override;

protected:
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<USceneComponent> Root;

	/** Solid as its own shape. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Stem;

	/** Solid as its own shape. It squashes when bounced on. */
	UPROPERTY(VisibleAnywhere, BlueprintReadOnly, Category = "Components")
	TObjectPtr<UStaticMeshComponent> Cap;

	/** Upward speed given to the ball, in cm/s. 1600 throws it about 13 m up. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float LaunchSpeed = 1600.f;

	/** How much of the ball's sideways speed it keeps, so a running bounce carries it forward. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float KeepHorizontal = 0.9f;

	/** Only a hit with the ball's centre above this height, relative to the actor and scaled with it, bounces it. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning")
	float BounceAboveHeight = 200.f;

	/** Played when it bounces the ball. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Effects")
	TObjectPtr<USoundBase> BounceSound;

private:
	FVector CapScale = FVector::OneVector;
	float SquashTime = -1.f;
	double LastBounceTime = -1.0;
};
