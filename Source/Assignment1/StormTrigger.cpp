// See StormTrigger.h for this class's purpose and connections.

#include "StormTrigger.h"

#include "WitheringStorm.h"

AStormTrigger::AStormTrigger()
{
#if WITH_EDITORONLY_DATA
	// The storm is always loaded, and World Partition warns when an actor that can unload references one that can't.
	bIsSpatiallyLoaded = false;
#endif
}

void AStormTrigger::OnBallOverlap(ASeedBall* Ball)
{
	if (Storm)
	{
		Storm->StartRising(Ball);
	}
}
