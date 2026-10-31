// Last Seed - a hidden collectible that counts toward the 3-star rating.
//
// Purpose: adds one to the level's petal count. There are 3 per level.
// Design pattern: template method (implements the OnCollected step of ALSPickupBase).
// Connections: collected by ASeedBall through ALSPickupBase. Reports to ALSGameMode, which keeps the count.

#pragma once

#include "CoreMinimal.h"
#include "LSPickupBase.h"
#include "GoldenPetal.generated.h"

UCLASS()
class ASSIGNMENT1_API AGoldenPetal : public ALSPickupBase
{
	GENERATED_BODY()

public:
	AGoldenPetal();

protected:
	virtual void OnCollected(ASeedBall* Ball) override;
};
