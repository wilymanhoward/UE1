#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "CollapsingStoneComponent.generated.h"

class ASeedBall;
class UBoxComponent;
class UPrimitiveComponent;

/** A stone pillar falls after the player leaves its cap; a respawn restores the whole pillar. */
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
	float CollapseDelay = 3.f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collapsing Stone", meta = (ClampMin = "0.1"))
	float FallDuration = 0.8f;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Collapsing Stone", meta = (ClampMin = "1"))
	float FallDistance = 1800.f;

	UFUNCTION(BlueprintPure, Category = "Collapsing Stone")
	bool IsCollapsing() const { return bCollapsing; }

protected:
	virtual void BeginPlay() override;
	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
	UFUNCTION()
	void HandleArrival(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex, bool bFromSweep, const FHitResult& SweepResult);
	UFUNCTION()
	void HandleDeparture(UPrimitiveComponent* OverlappedComponent, AActor* OtherActor, UPrimitiveComponent* OtherComp,
		int32 OtherBodyIndex);
	UFUNCTION()
	void Rebuild();
	void BeginCollapse();

	UPROPERTY(Transient)
	TObjectPtr<UBoxComponent> Sensor;
	UPROPERTY(Transient)
	TObjectPtr<ASeedBall> Ball;

	TArray<TWeakObjectPtr<AActor>> Pieces;
	TArray<FTransform> OriginalPoses;
	TArray<bool> OriginalCollision;
	TArray<bool> OriginalHidden;
	FTimerHandle CollapseTimer;
	float FallElapsed = 0.f;
	bool bTriggered = false;
	bool bCollapsing = false;
};
