#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "CollapsingStoneComponent.generated.h"

class ASeedBall;
class UAudioComponent;
class USoundBase;
class UPrimitiveComponent;

/** A crossing platform shakes on landing, falls after a short warning, and rebuilds on respawn. */
UCLASS(ClassGroup = (LastSeed), meta = (BlueprintSpawnableComponent))
class ASSIGNMENT1_API UCollapsingStoneComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UCollapsingStoneComponent();
	virtual void TickComponent(float DeltaTime, ELevelTick TickType, FActorComponentTickFunction* ThisTickFunction) override;

	/** Rocks below the owning cap, ordered from the bottom upward. */
	UPROPERTY(EditInstanceOnly, BlueprintReadWrite, Category = "Collapsing Stone")
	TArray<TObjectPtr<AActor>> SupportActors;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collapsing Stone", meta = (ClampMin = "0"))
	float CollapseDelay = 1.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collapsing Stone")
	TObjectPtr<USoundBase> ShakeSound;
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collapsing Stone")
	TObjectPtr<USoundBase> FallSound;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collapsing Stone", meta = (ClampMin = "0.1"))
	float FallDuration = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collapsing Stone", meta = (ClampMin = "1"))
	float FallDistance = 1800.f;

	UFUNCTION(BlueprintPure, Category = "Collapsing Stone")
	bool IsCollapsing() const { return bCollapsing; }
	UFUNCTION(BlueprintPure, Category = "Collapsing Stone")
	bool IsShaking() const { return bTriggered && !bCollapsing; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UFUNCTION()
	void HandleStep(UPrimitiveComponent* HitComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		FVector NormalImpulse, const FHitResult& Hit);
	UFUNCTION()
	void Rebuild();
	void BeginCollapse();

	UPROPERTY(Transient)
	TObjectPtr<UPrimitiveComponent> Surface;
	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> ShakeAudio;
	UPROPERTY(Transient)
	TObjectPtr<UAudioComponent> FallAudio;
	UPROPERTY(Transient)
	TObjectPtr<ASeedBall> Ball;

	TArray<TWeakObjectPtr<AActor>> Pieces;
	TArray<FTransform> OriginalPoses;
	TArray<bool> OriginalCollision;
	TArray<bool> OriginalHidden;
	FTimerHandle CollapseTimer;
	float FallElapsed = 0.f;
	float WarningElapsed = 0.f;
	bool bTriggered = false;
	bool bCollapsing = false;
};
