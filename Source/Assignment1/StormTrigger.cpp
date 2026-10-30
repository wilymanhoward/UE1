// See StormTrigger.h for this class's purpose and connections.

#include "StormTrigger.h"

#include "WitheringStorm.h"

void AStormTrigger::OnBallOverlap(ASeedBall* Ball)
{
	if (Storm)
	{
		Storm->StartRising(Ball);
	}
}
