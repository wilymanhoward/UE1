// Last Seed - data that survives level changes.
//
// Purpose: a game instance lives for the whole play session, so unlocked forms set in Level 1 are still
// there in Level 2. Phase 7 adds best scores, volume settings and save/load.
// Design pattern: none (a plain persistent data holder).
// Connections: ASeedBall asks IsFormUnlocked before switching. AFormFlower (Phase 2) calls UnlockForm.
// Selected in Config/DefaultEngine.ini through GameInstanceClass.

#pragma once

#include "CoreMinimal.h"
#include "Engine/GameInstance.h"
#include "SeedFormTypes.h"
#include "LSGameInstance.generated.h"

UCLASS()
class ASSIGNMENT1_API ULSGameInstance : public UGameInstance
{
	GENERATED_BODY()

public:
	UFUNCTION(BlueprintPure, Category = "Forms")
	bool IsFormUnlocked(ESeedForm Form) const { return UnlockedForms.Contains(Form); }

	UFUNCTION(BlueprintCallable, Category = "Forms")
	void UnlockForm(ESeedForm Form) { UnlockedForms.Add(Form); }

	UFUNCTION(BlueprintCallable, Category = "Forms")
	void UnlockAllForms();

protected:
	/** Forms the player may switch to. Seed is always available. */
	UPROPERTY(BlueprintReadOnly, Category = "Forms")
	TSet<ESeedForm> UnlockedForms = { ESeedForm::Seed };
};
