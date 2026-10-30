// See FormFlower.h for this class's purpose, pattern and connections.

#include "FormFlower.h"

#include "LSGameInstance.h"
#include "LSPlayerController.h"
#include "SeedBall.h"

void AFormFlower::OnCollected(ASeedBall* Ball)
{
	if (ULSGameInstance* GameInstance = GetGameInstance<ULSGameInstance>())
	{
		GameInstance->UnlockForm(FormToUnlock);
		GameInstance->SaveProgress();
	}

	if (ALSPlayerController* PlayerController = Ball->GetController<ALSPlayerController>())
	{
		PlayerController->ShowPrompt(PromptMessage, PromptDuration);
	}
}
