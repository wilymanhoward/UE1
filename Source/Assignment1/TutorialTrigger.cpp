// See TutorialTrigger.h for this class's purpose and connections.

#include "TutorialTrigger.h"

#include "LSPlayerController.h"
#include "SeedBall.h"

void ATutorialTrigger::OnBallOverlap(ASeedBall* Ball)
{
	if (bShown)
	{
		return;
	}
	bShown = true;

	if (ALSPlayerController* PlayerController = Ball->GetController<ALSPlayerController>())
	{
		PlayerController->ShowPrompt(Message, DisplayDuration);
	}
}
