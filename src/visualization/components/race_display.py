"""
RaceDisplay - Live race visualization orchestrator.

This component orchestrates the live race display, coordinating between
the three-way panel and service panels to show real-time race progress.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.align import Align

from ...race.models import ThreeWayRace, RaceParticipant
from ...api_clients import UnifiedAPIClient, create_chat_request
from .three_way_panel import ThreeWayPanel
from .service_panel import ServicePanel
from ..core.base_visualizer import LiveVisualizer


class RaceDisplay(LiveVisualizer):
    """Live race visualization orchestrator"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the race display
        
        Args:
            console: Rich console instance for output
        """
        super().__init__(console)
        self.three_way_panel = ThreeWayPanel("🔵 VLLM", "🟢 TGI", "🟠 OLLAMA")
        self.service_panels: Dict[str, ServicePanel] = {}
        self.current_race: Optional[ThreeWayRace] = None
    
    def render(self, data: ThreeWayRace) -> Layout:
        """Render the race display
        
        Args:
            data: The race data to display
            
        Returns:
            Complete race layout
        """
        self.current_race = data
        return self.create_race_layout()
    
    def create_layout(self) -> Layout:
        """Create the layout for live display
        
        Returns:
            Rich Layout object for the race
        """
        return self.three_way_panel.get_layout()
    
    def create_race_layout(self) -> Layout:
        """Create the complete race layout with prompt header
        
        Returns:
            Layout with prompt and three-way comparison
        """
        if not self.current_race:
            return self.three_way_panel.get_layout()
        
        # Create main layout with header and race area
        main_layout = Layout()
        main_layout.split_column(
            Layout(name="prompt_header", size=4),
            Layout(name="race_area")
        )
        
        # Add prompt header
        prompt_panel = Panel(
            Align.center(f"[bold white]{self.current_race.prompt}[/bold white]"),
            title="🧑 User Question",
            border_style="cyan"
        )
        main_layout["prompt_header"].update(prompt_panel)
        
        # Add race area
        main_layout["race_area"].update(self.three_way_panel.get_layout())
        
        return main_layout
    
    def update_layout(self, layout: Layout, data: ThreeWayRace):
        """Update the layout with new race data
        
        Args:
            layout: The layout to update
            data: New race data
        """
        self.current_race = data
        
        # Update service panels
        for service_name, participant in data.participants.items():
            self._update_service_display(service_name, participant)
    
    def setup_race(self, race: ThreeWayRace):
        """Setup the race display with participants
        
        Args:
            race: The race to setup
        """
        self.current_race = race
        
        # Create service panels for each participant
        for service_name, participant in race.participants.items():
            self.service_panels[service_name] = ServicePanel(participant)
        
        # Initialize all service displays
        self._initialize_service_displays()
    
    def _initialize_service_displays(self):
        """Initialize all service displays in ready state"""
        if not self.current_race:
            return
        
        for service_name, participant in self.current_race.participants.items():
            self._update_service_display(service_name, participant, "Ready", "cyan")
    
    def _update_service_display(self, service_name: str, participant: RaceParticipant, 
                               status: str = "Processing", status_color: str = "yellow", show_response: bool = False):
        """Update a specific service display
        
        Args:
            service_name: Name of the service
            participant: Updated participant data
            status: Current status
            status_color: Color for the status
            show_response: Whether to show the response content
        """
        if service_name not in self.service_panels:
            self.service_panels[service_name] = ServicePanel(participant)
        else:
            self.service_panels[service_name].update_participant(participant)
        
        # Create panel data
        panel_data = {
            "status": status,
            "status_color": status_color,
            "show_response": show_response or len(participant.current_response) > 0
        }
        
        # Get the display panel
        display_panel = self.service_panels[service_name].render(panel_data)
        
        # Update the appropriate column
        position_map = {
            "vllm": "left",
            "tgi": "center", 
            "ollama": "right"
        }
        
        if service_name in position_map:
            self.three_way_panel.update_column(position_map[service_name], display_panel.renderable)
    
    def mark_service_responding(self, service_name: str):
        """Mark a service as responding
        
        Args:
            service_name: Name of the responding service
        """
        if not self.current_race or service_name not in self.current_race.participants:
            return
        
        participant = self.current_race.participants[service_name]
        self._update_service_display(service_name, participant, "Responding...", "yellow")
    
    def mark_service_first_token(self, service_name: str):
        """Mark a service as having received first token
        
        Args:
            service_name: Name of the service
        """
        if not self.current_race or service_name not in self.current_race.participants:
            return
        
        participant = self.current_race.participants[service_name]
        self._update_service_display(service_name, participant, "Streaming...", "green")
    
    def mark_service_complete(self, service_name: str):
        """Mark a service as complete
        
        Args:
            service_name: Name of the completed service
        """
        if not self.current_race or service_name not in self.current_race.participants:
            return
        
        participant = self.current_race.participants[service_name]
        self._update_service_display(service_name, participant, "Complete", "green")
    
    def mark_service_error(self, service_name: str, error_message: str):
        """Mark a service as having an error
        
        Args:
            service_name: Name of the service
            error_message: Error message
        """
        if not self.current_race or service_name not in self.current_race.participants:
            return
        
        participant = self.current_race.participants[service_name]
        participant.error_message = error_message
        self._update_service_display(service_name, participant, f"Error: {error_message}", "red")
    
    def update_service_response(self, service_name: str, new_content: str):
        """Update a service's response content
        
        Args:
            service_name: Name of the service
            new_content: New response content
        """
        if not self.current_race or service_name not in self.current_race.participants:
            return
        
        participant = self.current_race.participants[service_name]
        participant.current_response = new_content
        
        # Determine status based on completion state
        if participant.is_complete:
            status = "Complete"
            status_color = "green"
        elif participant.first_token_time:
            status = "Streaming..."
            status_color = "yellow"
        else:
            status = "Processing..."
            status_color = "cyan"
        
        self._update_service_display(service_name, participant, status, status_color)
    
    async def run_live_race(self, race: ThreeWayRace, api_client: Optional[UnifiedAPIClient]) -> None:
        """Execute live race with real-time updates
        
        Args:
            race: The race to execute
            api_client: API client for making requests (None for demo mode)
        """
        self.setup_race(race)
        layout = self.create_race_layout()
        
        with Live(layout, refresh_per_second=10, console=self.console) as live:
            if api_client:
                # Real API mode - api_client is actually an APIAdapter
                await self._run_real_api_race(race, api_client, live)
            else:
                # Demo mode
                await self._run_demo_race(race, live)
            
            # Show final results
            await self._show_race_completion(live)
    
    async def _run_real_api_race(self, race: ThreeWayRace, api_adapter: 'APIAdapter', live: Live):
        """Run race with real APIs"""
        # Create request
        request = create_chat_request(race.prompt, max_tokens=256)
        
        # Start all services
        tasks = []
        for service_name in race.participants.keys():
            # Check if service is available through the adapter
            available_services = api_adapter.get_available_services()
            if service_name in available_services:
                task = asyncio.create_task(
                    self._run_real_service_stream(service_name, request, api_adapter, live)
                )
                tasks.append(task)
        
        # Wait for all services to complete
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_demo_race(self, race: ThreeWayRace, live: Live):
        """Run race with demo simulation"""
        from ...demo.simulation import DemoSimulator
        
        simulator = DemoSimulator()
        
        # Start all services concurrently
        tasks = []
        for service_name in race.participants.keys():
            task = asyncio.create_task(
                self._run_demo_service_stream(service_name, race, simulator, live)
            )
            tasks.append(task)
        
        # Wait for all services to complete
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _run_demo_service_stream(self, service_name: str, race: ThreeWayRace, simulator: 'DemoSimulator', live: Live):
        """Run demo streaming for a single service with live updates"""
        participant = race.participants[service_name]
        
        try:
            # Mark as starting
            self._update_service_display(service_name, participant, "Starting...", "yellow")
            live.update(self.create_race_layout())
            
            # Start streaming simulation
            participant.response_start_time = time.time()
            first_token = True
            full_response = ""
            
            async for token in simulator.simulate_streaming_response(service_name, race.prompt):
                if first_token:
                    # Mark first token received
                    participant.first_token_time = time.time()
                    race.mark_first_token(service_name)
                    first_token = False
                    
                    # Update display to show streaming
                    self._update_service_display(service_name, participant, "First token received!", "green")
                    live.update(self.create_race_layout())
                    await asyncio.sleep(0.1)  # Brief pause to show first token
                
                # Add token to response
                full_response += token
                participant.current_response = full_response
                participant.tokens_received += 1
                
                # Update display periodically
                if participant.tokens_received % 5 == 0:  # Update every 5 tokens
                    self._update_service_display(service_name, participant, "Streaming...", "cyan", show_response=True)
                    live.update(self.create_race_layout())
            
            # Mark as complete
            participant.is_complete = True
            race.mark_complete(service_name)
            self._update_service_display(service_name, participant, "Complete!", "green", show_response=True)
            live.update(self.create_race_layout())
            
        except Exception as e:
            participant.error_message = str(e)
            self._update_service_display(service_name, participant, f"Error: {str(e)}", "red")
            live.update(self.create_race_layout())
    
    async def _run_real_service_stream(self, service_name: str, request, api_adapter: 'APIAdapter', live: Live):
        """Run real API streaming for a single service with live updates"""
        if not self.current_race:
            return
        
        participant = self.current_race.participants[service_name]
        
        try:
            # Mark as starting
            self._update_service_display(service_name, participant, "Starting...", "yellow")
            live.update(self.create_race_layout())
            
            # Start streaming from real API
            participant.response_start_time = time.time()
            first_token = True
            full_response = ""
            
            async for token in api_adapter.stream_response(service_name, request):
                if first_token:
                    # Mark first token received
                    participant.first_token_time = time.time()
                    first_token = False
                    
                    # Update display to show streaming
                    self._update_service_display(service_name, participant, "First token received!", "green")
                    live.update(self.create_race_layout())
                    await asyncio.sleep(0.1)  # Brief pause to show first token
                
                # Add token to response
                full_response += token
                participant.current_response = full_response
                participant.tokens_received += 1
                
                # Update display periodically
                if participant.tokens_received % 10 == 0:  # Update every 10 tokens for real APIs
                    self._update_service_display(service_name, participant, "Streaming...", "cyan", show_response=True)
                    live.update(self.create_race_layout())
            
            # Mark as complete
            participant.is_complete = True
            self._update_service_display(service_name, participant, "Complete!", "green", show_response=True)
            live.update(self.create_race_layout())
            
        except Exception as e:
            participant.error_message = str(e)
            self._update_service_display(service_name, participant, f"Error: {str(e)}", "red")
            live.update(self.create_race_layout())
    
    async def _run_service_stream(self, service_name: str, request, api_client: UnifiedAPIClient, live: Live):
        """Run streaming for a single service (legacy method)
        
        Args:
            service_name: Name of the service
            request: Generation request
            api_client: API client
            live: Live display
        """
        try:
            self.mark_service_responding(service_name)
            
            first_token = True
            async for chunk in api_client.stream_generate(service_name, request):
                if first_token:
                    self.mark_service_first_token(service_name)
                    first_token = False
                
                # Update response content
                if self.current_race and service_name in self.current_race.participants:
                    participant = self.current_race.participants[service_name]
                    participant.current_response += chunk
                    self.update_service_response(service_name, participant.current_response)
            
            self.mark_service_complete(service_name)
            
        except Exception as e:
            self.mark_service_error(service_name, str(e))
    
    async def _show_race_completion(self, live: Live):
        """Show race completion message
        
        Args:
            live: Live display
        """
        # Pause for dramatic effect
        await asyncio.sleep(2)
        
        # Could add completion effects here
        pass
    
    async def wait_for_user_continuation(self) -> None:
        """Handle user interaction for demo pacing"""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: input("\n⏸️  Press Enter to continue to summary...")
            )
        except (KeyboardInterrupt, EOFError):
            pass
