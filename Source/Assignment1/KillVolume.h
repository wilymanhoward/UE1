// Last Seed - a fall-off zone that sends the ball back to its checkpoint.
//
// Purpose: place below gaps and ledges. Any ball entering it dies and respawns. Over lava it can name the lava
// surface, and then it only kills while that surface is what the ball rests on, so floors laid over the lava are safe.
// Design pattern: none. It overrides one ILSInteractable function.
// Connections: touched by ASeedBall through ILSInteractable. Calls ASeedBall::Die.

#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "KillVolume.generated.h"

class UMaterialInterface;
class UNiagaraSystem;
class USoundBase;

UCLASS()
class ASSIGNMENT1_API AKillVolume : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	AKillVolume();

	virtual void OnBallOverlap(ASeedBall* Ball) override;
	virtual void Tick(float DeltaSeconds) override;

	/** The lava this box sits under. Set: the ball dies only when this (or nothing) is right below it, so any floor,
	 *  rock or stone over the lava keeps it safe. Empty: the ball dies as soon as it enters. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Burn")
	TObjectPtr<AActor> LavaSurface;

	/** Lava: effects played where the ball touches before it dies, so it reads as burning up. Empty for a plain fall. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Burn")
	TArray<TObjectPtr<UNiagaraSystem>> BurnEffects;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Burn")
	TObjectPtr<USoundBase> BurnSound;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Burn", meta = (ClampMin = "0"))
	float BurnEffectScale = 1.5f;

	/** Lava: molten droplets of this material burst up where the ball goes in (ALSLavaSplash). Empty for none. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Burn")
	TObjectPtr<UMaterialInterface> SplashMaterial;

	/** How big and high the splash is; 1 throws droplets about 3-4 m up. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Burn", meta = (ClampMin = "0.1"))
	float SplashSize = 1.f;

private:
	bool IsOnLava(const ASeedBall* Ball) const;
	void Burn(ASeedBall* Ball);
};
