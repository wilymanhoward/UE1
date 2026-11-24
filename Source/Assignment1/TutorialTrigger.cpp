// See TutorialTrigger.h for this class's purpose and connections.

#include "TutorialTrigger.h"

#include "Components/BoxComponent.h"
#include "Kismet/GameplayStatics.h"
#include "LSPlayerController.h"
#include "SeedBall.h"

void ATutorialTrigger::ConfigurePrompt(const FText& InTitle, const FText& InMessage, const FVector& HalfExtent)
{
	Title = InTitle;
	Message = InMessage;
	Box->SetBoxExtent(HalfExtent);
}

void ATutorialTrigger::OnBallOverlap(ASeedBall* Ball)
{
	if (bShown)
	{
		return;
	}
	bShown = true;

	// Older Emberwood maps still place this taunt before the finale's reaction.
	if (Message.ToString().Contains(TEXT("gathered your precious little sparks")))
	{
		return;
	}

	if (ALSPlayerController* PlayerController = Ball->GetController<ALSPlayerController>())
	{
		if (Title.IsEmpty())
		{
			PlayerController->ShowPrompt(Message, DisplayDuration);
		}
		else
		{
			PlayerController->ShowTitledPrompt(Title, Message, DisplayDuration);
		}
	}
	UGameplayStatics::PlaySound2D(this, Voice);
}
