// Last Seed - the pickup that gives the seed a new form.
//
// Purpose: unlocks one form, saves that straight away, and shows a prompt teaching the new ability.
// Design pattern: template method (implements the OnCollected step of ALSPickupBase).
// Connections: collected by ASeedBall through ALSPickupBase. Writes to ULSGameInstance, so the unlock
// lasts across levels, and shows its prompt through ALSPlayerController.

#pragma once

#include "CoreMinimal.h"
#include "LSPickupBase.h"
#include "SeedFormTypes.h"
#include "FormFlower.generated.h"

UCLASS()
class ASSIGNMENT1_API AFormFlower : public ALSPickupBase
{
	GENERATED_BODY()

protected:
	virtual void OnCollected(ASeedBall* Ball) override;

	/** The form this flower unlocks. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Form Flower")
	ESeedForm FormToUnlock = ESeedForm::Stone;

	/** Tutorial text shown when collected, such as "Stone Shell unlocked! Press 2 to transform." */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Form Flower")
	FText PromptMessage;

	/** How long the prompt stays on screen, in seconds. */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Tuning", meta = (ClampMin = "0"))
	float PromptDuration = 5.f;
};
