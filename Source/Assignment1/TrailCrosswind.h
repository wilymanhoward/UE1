#pragma once

#include "CoreMinimal.h"
#include "LSVolumeBase.h"
#include "TrailCrosswind.generated.h"

class UStaticMeshComponent;

UCLASS()
class ASSIGNMENT1_API ATrailCrosswind : public ALSVolumeBase
{
	GENERATED_BODY()

public:
	ATrailCrosswind();
	virtual void Tick(float DeltaSeconds) override;

protected:
	virtual void BeginPlay() override;

private:
	UPROPERTY()
	TArray<TObjectPtr<UStaticMeshComponent>> WindShapes;
};
